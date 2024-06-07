# Use the kit 105.1.2 streaming base image available publicly via NVIDIA NGC
FROM nvcr.io/nvidia/omniverse/ov-kit-appstreaming:105.1.2-135279.16b4b239

# Cleanup embedded kit-sdk-launcher package as usd-viewer is a full package with kit-sdk
RUN rm -rf /opt/nvidia/omniverse/kit-sdk-launcher

# Copy the usd-viewer application package from the _build/packages directory into the containers /app directory.
COPY --chown=ubuntu:ubuntu _build/packages/ /app/

# Unzip the application package into the container's /app directory and then delete the application package
WORKDIR /app
RUN PACKAGE_FILE=$(find . -type f -name "*-linux-x86_64.zip") && unzip $PACKAGE_FILE -d . && rm $PACKAGE_FILE


# Pull in any additional required dependencies
RUN /app/pull_kit_sdk.sh

# Copy the usd-viewer ovc kit file from the repos source/apps directory into the container image.
COPY --chown=ubuntu:ubuntu source/apps/omni.usd_viewer.ovc.kit /app/apps/omni.usd_viewer.ovc.kit

# Copy the startup.sh script from the repos source/scripts directory.
# This is what will be called when the container image is started.
# Edit the startup file to point to the first sample file (above).
COPY --chown=ubuntu:ubuntu source/scripts/startup.sh /startup.sh
RUN chmod +x /startup.sh

# This specifies the container's default entrypoint that will be called by "> docker run".
ENTRYPOINT [ "/startup.sh" ]
