import wmi

serverName = "WIN-TEST-1"
connection = wmi.connect_server(server=serverName, namespace=r"root\virtualization")
wmiServerConnection = wmi.WMI(wmi=connection)
vmManagement = wmiServerConnection.Msvm_VirtualSystemManagementService()
vmData = wmiServerConnection.Msvm_VirtualSystemGlobalSettingData.new()
vmData.ElementName = "Hortonworks Sandbox 2.0"
vmManagement[0].DefineVirtualSystem([], None, vmData.GetText_(1))

