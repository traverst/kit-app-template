# Containerizing usd-viewer kit-application

## Overview

This document outlines steps to containerize and locally test the usd-viewer sample kit-application in preparation for deploying it to an Omniverse Application Streaming instance or any suitable Kubernetes cluster.


### Reqirements:

- **Access to a linux desktop**
- **~30GB free disk space**
- **Docker**
- **LFS support is required for cloning with git**

---


## 1 Install Docker and the nvidia-container-toolkit

**Only run sections explicitly called for in the instructions!**

Follow the standard instructions to install Docker and the *nvidia-container-toolkit* in [**INSTALLATION SECTION**](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installation) on the system you are using to create the usd-viewer container image. **You may have to prepend `sudo` to second step.** 

> **NOTE:**  Enabling non-sudo support for Docker, which is described in the official Docker post-install guide, can ease development and is reflected in the instructions below.  Appending “sudo” will otherwise be required, which may have other implications around file and folder permissions.

Configure the nvidia container runtime with docker by following [**CONFIGURE DOCKER SECTION**](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#configuring-docker) of the instructions. **You may skip the "Rootless Mode" Section**

## 2 Create a clean release build of usd-viewer

> **NOTE:** Docker must be installed and **git LFS** is required.

#### 2a Clone `105.1-viewer` branch of `kit-app-template`

```bash
git clone -b 105.1-viewer https://github.com/NVIDIA-Omniverse/kit-app-template.git
```

#### 2b Navigate to Cloned Directory

```bash
cd kit-app-template
```


#### 2c Create and Configure New Application From Template

```bash
./repo.sh template new
```

> **Note:** If this is your first time running the `template new` tool, you'll be prompted to accept the Omniverse Licensing Terms after a ~30 second pause.

**Follow the prompt instructions and use all default values.**

> **NOTE:** If using a custom .kit file name, you will need to edit `source/apps/omni.usd_viewer.ovc.kit` and `source/scripts/startup.sh` - search and replace `my_company.my_usd_viewer` with custom name.


#### 2d Clean build directory

```bash
./repo.sh build -c
```


#### 2e Build a release version

```bash
./repo.sh build
```

**Ensure that you see a similar message when build completes:**

```
BUILD (RELEASE) SUCCEEDED (Took XX.YY seconds)
```


## 3 Create a fat application package

In order to create a container image of a kit application, we must ensure that we have all of its required dependencies.  Creating a fat application package leverages the NVIDIA provided repo tool to do exactly that.  It identifies all dependencies required by the kit application and packages them, in a structured way, into a completely contained .zip file.

**Execute in usd-viewer directory:**

```bash
./repo.sh package
```

**Ensure that you see a similar message when the packaging ends:**
```
Package Created: [template_root]/_build/packages/kit-app-template-fat@106.0.0-rc.1-linux-x86_64.zip (Took 226.32 seconds)
```

This creates a .zip file in the _build/packages directory


## 4 Build the container

**Make sure you [installed and configured docker first.](#1-install-docker-and-the-nvidia-container-toolkit)**

Building a container is straightforward, once you have a properly configured Dockerfile.

**Run the docker command in the cloned repo directory to build the container image of the usd-viewer kit application, using the tag usd-viewer, version 0.2.0**

```bash 
docker build . -t usd-viewer:0.2.0
```

**Ensure that you see a similar message when build completes:**

```
=> => writing image sha256:9f3738248a15b521fa48ba4b83c9f12e31542b5352ac0638bb523628c25a 0.0s 
=> => naming to docker.io/library/usd-viewer:0.2.0
```

**View the local docker images:**

```bash 
docker images
```

**Ensure that usd-viewer is listed:**

```
REPOSITORY         TAG          IMAGE ID       CREATED         SIZE

usd-viewer         0.2.0        9f37382d4574   2 minutes ago   12.4GB
````


## 5 Running the container

Now that we have created the usd-viewer container, we want to ensure that it runs.  We will follow a similar process for testing the container as we did when trying running the newly built usd-viewer kit application.  We will run the container, which will start the streaming process.  To test, we will directly connect to it via the web-viewer-sample as we did previously, no changes required.

**If this isnt a clean run, make sure that you [stop any existing dockers.](#6c-kill-docker-container)**

#### Run the container:
```bash
docker run -d --runtime=nvidia --gpus all --net=host usd-viewer:0.2.0
```
This starts the usd-viewer container running.  Other than the output in the shell, you will not see anything.

### Initial startup may take between 5-10 minutes!

**The Omniverse Application Streaming API platform leverages a shared shader cache to mitigate subsequent shader compilation across all of the pods in the cluster, however - *when running locally from a container image, this is not available.***


## 6 Check status / kill containers

#### 6a Get container [NAME]

**List all of the running containers:**
```bash
docker ps
```

**Output:**
```
CONTAINER ID   IMAGE              COMMAND                  CREATED          STATUS          PORTS                    NAMES
67742e0ce56e   usd-viewer:0.2.0   "/startup.sh"            17 seconds ago   Up 12 seconds                            gifted_hellman
b72d62d539d3   my_other_app:1.3.7 "python /app/linux_e…"   3 weeks ago      Up 2 days       0.0.0.0:9101->9101/tcp   my_other_app_container
```

Look for **usd-viewer:0.2.0** - note that it is identified by a unique NAME - in this output it is `gifted_hellman`.

#### 6b Check container logs

Keep running this command every few minutes until you see `stage01.usd opened successfully` ( press up arrow and enter to repeat ). There will be a pause in shader compilation updates which is normal.
```bash
docker logs [NAME] | grep -Ei "Waiting for compilation|stage01.usd opened successfully"
```

 **Expect to wait around 5-10 minutes before stage is loaded.**

> **TIP:** `grep` highlights output that contains the pattern in quotes.

> **TIP:** You can add `--tail 100` after [NAME] to limit output to last 100 lines. 

***If you see `stage01.usd opened successfully` - Congratulations! You’ve have a streamable kit application - ready for deployment to any Kubernetes cluster, such as an Omniverse Application Streaming instance. [Go ahead and stream it](#connect-via-web-viewer-sample).***

#### 6c Kill docker container
This will shut down docker using its [[NAME]](#6a-get-container-name), you should do this only if you are about to start a docker and there is an existing one already running. You should have only one container running at any given time.
```bash
docker kill [NAME]
```


## Connect via web-viewer-sample

If you havent already, follow the documentation to install the latest version of `web-viewer-sample`

> **NOTE:** You can stream from external machines by editing `"server": "IP"` in **stream.config.json** located in web-viewer-sample root.

Before starting web-viewers, you should [**confirm that container is ready to stream.**](#6b-check-container-logs)

**Now run this in `web-viewer-sample` root:**
```bash
npm run dev
```

**Follow the on-screen directions:**

- press 'h' + enter to see the keyboard commands
- press ‘o’ + enter to open the default browser automatically with the correct address.

Otherwise, open Chrome and access the URL after **Local:** in the output above.


### *Help!  I got a black screen*
This can occur if the shaders are still being compiled when the web client connects to the streaming kit application. Depending on the number of unique shaders, **it can take up to 10 minutes to compile all of them.** Closing and re-opening the browser tab is usually the most effective method for resolving this issue. **When deployed to a Omniverse Application Streaming API instance, this is mitigated by leveraging a shared shader cache across all of the pods in the cluster.**


## Next Steps ( optional )

There are a few additional steps required to deploy your locally built usd-viewer container image to an Omniverse Application Streaming Instance, which are outside the scope of this document and likely require assistance from members of your cloud infrastructure team.

### Pushing your container image to a repository

Your usd-viewer container image has been built locally and resides in your local docker instance.  In order for it to be broadly deployable, it needs to be registered with a container registry.  A container registry is a repository that stores container images to facilitate deployments to kubernetes clusters.  These can be an entirely self-hosted registry or a private or public registry in a commercial repository such as NVIDIA’s NGC.  Where to register your container is an important decision and you must ensure that what-ever kubernetes clusters you want to deploy to have access to your usd-viewer container image in the registry.

Registering your new container image with a repository is called “pushing” and is done by properly tagging your container image and then pushing it.

A simple example of pushing a locally created container to NGC, using a pseudo company tag of “my_company”.

**Login to NVIDIA's NGC (ncr = nvidia container registry).**
```bash
docker login ncr.io
```

**Add the registry information to the container image, using the tag command.**
```bash
docker usd-viewer:0.2.0 nvcr.io/my_company/omniverse/usd-viewer:0.2.0
```

**Now push the image to the registry**
```bash
docker push nvcr.io/my_company/omniverse/usd-viewer:0.2.0
```


## Deploying to an Omniverse Application Streaming Instance

Deploying a kit application to an Omniverse Application Streaming Instance involves modifying the configuration information used by the application service running in the instance.  It is quite likely that access to the instance is restricted and will require you to work with members of your infrastructure or SRE team.

Information on how to “Add an Application” is contained within the deployment documentation provided as part of the Omniverse Application Streaming Instance.

At time of this writing, it was in the *Deploying & Configuring Containerized Kit Applications* document.

**Connecting the Web Client to an Omniverse Application Streaming Instance**

Once the usd-viewer container image has been registered with an Omniverse Application Streaming Instance you can continue with the next guide.



