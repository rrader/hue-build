get_s3_directory() {
	if [ -z "$RELEASE" ]; then
		echo "dev"
	else
		echo "stable"
	fi
}