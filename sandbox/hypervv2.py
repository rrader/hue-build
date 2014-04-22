# Used code from openstack-nova nova/virt/hyperv.py and openstack-quantum

# Script for Hyper-V API V2

import os
import time
import logging
import uuid
import urllib
import time
from optparse import OptionParser
import uuid
import wmi

SERVER = "HYPER-V"

vhdfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image.vhd")

INSTANCE = {
    "name": "Hortonworks Sandbox 2.0",
    "memory_mb": 2048,
    "vcpus": 2,
    "vhdfile": vhdfile,
    "int_network": "Sandbox Network",
}

LOG = logging.getLogger('hyperv')

HYPERV_VM_STATE_ENABLED = 2
HYPERV_VM_STATE_DISABLED = 3
HYPERV_VM_STATE_REBOOT = 10
HYPERV_VM_STATE_RESET = 11
HYPERV_VM_STATE_PAUSED = 32768
HYPERV_VM_STATE_SUSPENDED = 32769

WMI_JOB_STATUS_STARTED = 4096
WMI_JOB_STATE_RUNNING = 4
WMI_JOB_STATE_COMPLETED = 7

def _wait_for_job(job_path):
    job_wmi_path = job_path.replace('\\', '/')
    job = wmi.WMI(moniker=job_wmi_path)

    while job.JobState == WMI_JOB_STATE_RUNNING:
        time.sleep(1.)
        job = wmi.WMI(moniker=job_wmi_path)
    LOG.debug("Job %s FINISHED; %s; %s" % (job_path, job.JobStatus, job.GetError()))
    return job


class Instance(object):
    def _find_internal_network(self, int_network):
        switch = self.conn.Msvm_VirtualEthernetSwitch(ElementName=int_network)
        print(switch)
        if not switch:
            msg = "Network switch '%s' not found" % int_network
            LOG.error(msg)
            raise ValueError(msg)
        return switch[0]

    def __init__(self, hyperv, name, vhdfile=None, memory_mb=1024, vcpus=1, int_network=None):
        self.hyperv = hyperv
        self.conn = self.hyperv.conn
        self.name = name
        self.vhdfile = vhdfile
        self.memory_mb = memory_mb
        self.vcpus = vcpus
        self.int_network = int_network

    def load_existing(self):
        LOG.info("Loading existing configuration '%s'" % self.name)
        self.vm = self.conn.Msvm_ComputerSystem(ElementName=self.name)[0]

    def create(self):
        self._create(self.name)

        self.set_memory(self.memory_mb)
        self.set_cpus(self.vcpus)

        if self.vhdfile:
            self.add_vhd(self.vhdfile)

        if self.int_network:
            self.create_nic(self.int_network)

    def _create(self, name):
        data = self.conn.Msvm_VirtualSystemSettingData.new()
        data.ElementName = name

        self.hyperv.management.DefineSystem(ResourceSettings=[],
                                            ReferenceConfiguration=None,
                                            SystemSettings=data.GetText_(1))

        self.vm = self.conn.Msvm_ComputerSystem(ElementName=name)[0]

        # get settings
        self.vm_settings = self.vm.associators(
            wmi_result_class='Msvm_VirtualSystemSettingData')
        self.vm_setting = self.vm_settings[0]
        self.mem_setting = self.vm_setting.associators(
            wmi_result_class='Msvm_MemorySettingData')[0]
        self.cpu_settings = self.vm_setting.associators(
            wmi_result_class='Msvm_ProcessorSettingData')[0]
        self.rasds = self.vm_settings[0].associators(
            wmi_result_class='MSVM_ResourceAllocationSettingData')
        LOG.info('Created vm %s...', name)

    def _clone_wmi_obj(self, wmi_class, wmi_obj):
        """Clone a WMI object"""
        cl = self.conn.__getattr__(wmi_class) # get the class
        newinst = cl.new()
        #Copy the properties from the original.
        for prop in wmi_obj._properties:
            newinst.Properties_.Item(prop).Value = \
                wmi_obj.Properties_.Item(prop).Value
        return newinst

    def set_memory(self, memory_mb):
        mem = long(str(memory_mb))
        self.mem_setting.VirtualQuantity = mem
        self.mem_setting.Reservation = mem
        self.mem_setting.Limit = mem
        self.hyperv.management.ModifyResourceSettings(ResourceSettings=[self.mem_setting.GetText_(1)])
        LOG.info('Set memory [%s MB] for vm %s...', mem, self.name)

    def set_cpus(self, vcpus):
        vcpus = long(vcpus)
        self.cpu_settings.VirtualQuantity = vcpus
        self.cpu_settings.Reservation = vcpus
        self.cpu_settings.Limit = 100000 # static assignment to 100%
        self.hyperv.management.ModifyResourceSettings(ResourceSettings=[self.cpu_settings.GetText_(1)])
        LOG.info('Set vcpus [%s] for vm %s...', vcpus, self.name)

    def add_vhd(self, vhdfile):
        ide_controller = [r for r in self.rasds
                          if r.ResourceSubType == 'Microsoft:Hyper-V:Emulated IDE Controller' and r.Address == "0"][0]
        disk_default = self.conn.query(
            "SELECT * FROM Msvm_ResourceAllocationSettingData \
WHERE ResourceSubType LIKE 'Microsoft:Hyper-V:Synthetic Disk Drive'\
AND InstanceID LIKE '%Default%'")[0]
        disk_drive = self._clone_wmi_obj(
            'Msvm_ResourceAllocationSettingData', disk_default)
        disk_drive.Parent = ide_controller.path_()
        disk_drive.Address = 0
        disk_drive.AddressOnParent = 0
        res_xml = [disk_drive.GetText_(1)]
        job_path, new_resources, _ = self.hyperv.management.AddResourceSettings(self.vm.path_(),
                                                                                res_xml)
        disk_drive_path = new_resources[0]
        LOG.info('New disk drive path is %s', disk_drive_path)
        #Find the default VHD disk object.
        vhd_default = self.conn.query(
            "SELECT * FROM Msvm_StorageAllocationSettingData \
WHERE ResourceSubType = 'Microsoft:Hyper-V:Virtual Hard Disk' AND \
InstanceID LIKE '%%\\Default' ")[0]
        #Clone the default and point it to the image file.
        vhd_disk = self._clone_wmi_obj(
            'Msvm_StorageAllocationSettingData', vhd_default)
        vhd_disk.Parent = disk_drive_path
        vhd_disk.HostResource = [vhdfile]
        self.hyperv.management.AddResourceSettings(self.vm.path_(),
                                                   [vhd_disk.GetText_(1)])
        LOG.info('Created disk [%s] for vm %s...', vhdfile, self.name)

    def create_nic(self, int_network):
        switch = self._find_internal_network(int_network)

        # http://blogs.msdn.com/b/taylorb/archive/2013/07/15/adding-a-network-adapter-to-a-vm-using-the-hyper-v-wmi-v2-namespace.aspx
        resource_pool = self.conn.query("SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Synthetic Ethernet Port' AND Primordial = True ")[0]
        allocation_capabilities = [x for x in resource_pool.associators() if "Msvm_AllocationCapabilities" in x.path_()][0]
        new_nic_data = [x for x in allocation_capabilities.associators() if "SyntheticEthernetPortSettingData" in x.path_()][0]

        LOG.info("Created switch port %s on switch %s", self.name, switch.path_())
        new_nic_data.Connection = [""]
        new_nic_data.ElementName = "SandboxNIC"
        new_nic_data.StaticMacAddress = False
        new_nic_data.Address = "000000000000"
        new_nic_data.InstanceID = None
        new_nic_data.AddressOnParent = None
        new_nic_data.Parent = None
        new_nic_data.ClusterMonitored = True
        new_nic_data.VirtualSystemIdentifiers = ['{' + str(uuid.uuid4()) + '}']
        
        self.hyperv.management.AddResourceSettings(self.vm.path_(),
                                                   [new_nic_data.GetText_(2)])

        new_nic_data = self.conn.Msvm_SyntheticEthernetPortSettingData(ElementName="SandboxNIC")[0]

        eth_ports_data = self.conn.Msvm_EthernetPortAllocationSettingData()
        default_eth_port_data = [n for n in eth_ports_data
                            if n.InstanceID.rfind('Default') > 0]
        eth_port_data = self._clone_wmi_obj(
            'Msvm_EthernetPortAllocationSettingData',
            default_eth_port_data[0])
        eth_port_data.HostResource = [switch.path_()]
        eth_port_data.Parent = new_nic_data.path_()
        self.hyperv.management.AddResourceSettings(self.vm.path_(),
                                                   [eth_port_data.GetText_(1)])
        LOG.info("Created nic for %s ", self.name)

    def export(self, path):
        export_setting_data_default = self.conn.Msvm_VirtualSystemExportSettingData()[0]
        export_setting_data = self._clone_wmi_obj(
            'Msvm_VirtualSystemExportSettingData', export_setting_data_default)
        export_setting_data.CopyVmStorage = True
        export_setting_data.CopyVmRuntimeInformation = True
        export_setting_data.CreateVmExportSubdirectory = True
        export_setting_data.CopySnapshotConfiguration = 1
        export_setting_data.SnapshotVirtualSystem = None
        export_setting_data.InstanceID = None
        job, ret_code = self.hyperv.management.ExportSystemDefinition(self.vm.path_(), path, export_setting_data.path_())
        LOG.info("Started exporting %s ", self.name)
        if ret_code == WMI_JOB_STATUS_STARTED:
            _wait_for_job(job)
        LOG.info("Finished exporting %s ", self.name)

    def start(self):
        job, ret_val = self.vm.RequestStateChange(HYPERV_VM_STATE_ENABLED)
        if ret_val == WMI_JOB_STATUS_STARTED:
            _wait_for_job(job)
        LOG.info("Booting %s ", self.name)

    def stop(self):
        LOG.info("Stopping %s ...", self.name)
        job, ret_val = self.vm.RequestStateChange(HYPERV_VM_STATE_DISABLED)
        if ret_val == WMI_JOB_STATUS_STARTED:
            _wait_for_job(job)
        LOG.info("Stopped %s ", self.name)

    def destroy(self):
        self.stop()
        job, ret_code = self.hyperv.management.DestroySystem(self.vm.path_())
        if ret_code == WMI_JOB_STATUS_STARTED:
            _wait_for_job(job)


class HyperV(object):
    def __init__(self, server_name):
        connection = wmi.connect_server(server=server_name, namespace=r"root\virtualization\v2")
        self.conn = wmi.WMI(wmi=connection)
        self.management = self.conn.Msvm_VirtualSystemManagementService()[0]

    def create(self, *args, **kwargs):
        LOG.info('Creating machine with options: %s' % kwargs)
        vm = Instance(self, *args, **kwargs)
        vm.create()
        return vm

    def destroy(self, *args, **kwargs):
        name = kwargs.get("name")
        while True:
            try:
                vm = Instance(self, name)
                vm.load_existing()
                vm.destroy()
            except IndexError:
                break
        LOG.info("Old machines '%s' DESTROYED" % name)


def download(url, path):
    def reporthook(count, block_size, total_size):
        global start_time, prev_print
        if count == 0:
            start_time = time.time()
            prev_print = time.time()
            return
        if time.time() - prev_print < 15:
            return
        duration = time.time() - start_time
        prev_print = time.time()
        progress_size = int(count * block_size)
        speed = int(progress_size / (1024 * duration))
        percent = int(count * block_size * 100 / total_size)
        status = ("%d%%, %d MB, %d KB/s, %d seconds passed" %
                        (percent, progress_size / (1024 * 1024), speed, duration))
        LOG.info(status)
    LOG.info("retrieving '%s'->'%s'" % (options.file, path))
    try:
        os.remove(path)
    except OSError:
        pass
    urllib.urlretrieve(url, path, reporthook)
    LOG.info("retrieving '%s' DONE" % (options.file))


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--sleep", dest="sleep",
                  help="sleep after boot (secs)", metavar="SLEEP")
    parser.add_option("-f", "--file", dest="file",
                  help="URL to VHD", metavar="FILE")
    parser.add_option("-m", "--mem", dest="memory",
                  help="memory (MB)", metavar="MEMORY")
    parser.add_option("-e", "--export", dest="export",
                  help="export machine (true or false)")
    parser.add_option("-i", "--spinup", dest="spinup",
                  help="spinup new machine (true or false)")


    (options, args) = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    if options.memory:
        INSTANCE['memory_mb'] = int(options.memory)

    hyperv = HyperV(SERVER)

    if not options.spinup or options.spinup == 'true':
        hyperv.destroy(**INSTANCE)

        if options.file:
            LOG.info("Downloading VHD file '%s'" % options.file)
            download(options.file, INSTANCE['vhdfile'])

        instance = hyperv.create(**INSTANCE)
    else:
        instance = Instance(hyperv, name=INSTANCE['name'])
        instance.load_existing()

    if options.export and options.export != 'false':
        instance.export("C:\Sandbox-Exported")
    instance.start()

    if options.sleep:
        LOG.info("Waiting '%s'" % options.sleep)
        time.sleep(int(options.sleep))
