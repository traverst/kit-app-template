# Omniverse Viewer Kit App Template

<p align="center">
  <img src="readme-assets/usd_viewer.jpg" width=100% />
</p>

**Based On:** `Omniverse Kit SDK 105.1`


## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Templates](#templates)
    - [Applications](#applications)
    - [Extensions](#extensions)
- [Prerequisites and Environment Setup](#prerequisites-and-environment-setup)
- [Repository Structure](#repository-structure)
- [Tools](#tools)
- [License](#license)
- [Additional Resources](#additional-resources)
- [Contributing](#contributing)


## Overview

Welcome to `kit-app-template`, an essential toolkit for developers diving into GPU-accelerated application development within the NVIDIA Omniverse ecosystem. This repository provides streamlined templates and tools designed to simplify the creation of high-performance OpenUSD-based applications powered by the Omniverse Kit SDK.


### About Omniverse Kit SDK

The Omniverse Kit SDK empowers developers to build immersive 3D applications with ease. Key features include:
- **Language Support:** Develop in Python or C++, offering flexibility and power to a wide range of developers.
- **OpenUSD Foundation:** Utilize Open Universal Scene Description (OpenUSD) for creating, manipulating, and rendering rich 3D content.
- **GPU Acceleration:** Leverage GPU-accelerated capabilities for high-fidelity visualization and simulation.
- **Extensibility:**  Easily build specialized Extensions that provide dynamic user interfaces, integration with various systems, and provide direct control over OpenUSD data, making it versatile for numerous applications.


## Templates

`kit-app-template` features an array of configurable templates for `Extensions` and `Applications`, catering to a range of desired development starting points from minimal to feature rich.


### Applications

Begin constructing Omniverse Applications using these templates

- **[Usd Viewer](./templates/apps/usd_viewer)**: The USD Viewer App Template is designed to provide a robust starting point for developers looking to create streaming Omniverse Applications. This template showcases an RTX viewport, app streaming, and messaging support.


### Extensions

Enhance Omniverse capabilities with extension templates:

- **[Usd Viewer Setup](./templates/extensions/usd_viewer.setup)**: Some applications require setup extensions to function as intended. In the case of USD Viewer, this extension runs automatically during application creation.


## Prerequisites and Environment Setup

To kickstart your development journey with Omniverse Applications and Extensions, your system should adhere to the following specifications:

- [**Technical Requirements**](https://docs.omniverse.nvidia.com/platform/latest/common/technical-requirements.html)
- **Software Dependencies**:
  - Required : Git
  - Recommended : Docker
  - Recommended : VSCode (or your preferred IDE)
  - LFS support is required for cloning with `git`.


## Repository Structure

| Directory Item   | Purpose                                                    |
|------------------|------------------------------------------------------------|
| .vscode          | VS Code configuration details and helper tasks             |
| readme-assets/   | Images and additional repository documentation             |
| templates/       | Template Applications and Extensions.                      |
| tools/           | Tooling settings and repository specific (local) tools     |
| .editorconfig    | [EditorConfig](https://editorconfig.org/) file.            |
| .gitattributes   | Git configuration.                                         |
| .gitignore       | Git configuration.                                         |
| LICENSE          | License for the repo.                                      |
| README.md        | Project information.                                       |
| premake5.lua     | Build configuration - such as what apps to build.          |
| repo.bat         | Windows repo tool entry point.                             |
| repo.sh          | Linux repo tool entry point.                               |
| repo.toml        | Top level configuration of repo tools.                     |
| repo_tools.toml  | Setup of local, repository specific tools                  |


## Quick Start

This section guides you through creating your first Kit SDK-based Application using the `kit-app-template` repository. For a more comprehensive explanation of functionality previewed here, reference the following [Tutorial](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template) for an in-depth exploration.

### 1. Clone the Repository

Begin by cloning the `105.1-viewer` branch of `kit-app-template` to your local workspace.

*If you are using windows, it is recommended to clone to a short directory path like `C:/repos` to avoid any file-path length issues (unless your workspace is configured to remove these limits).*

## Repository Structure
#### 1a. Clone

***NOTE:*  `-b 105.1-viewer` in following command specifies the branch.**

```bash
git clone -b 105.1-viewer https://github.com/NVIDIA-Omniverse/kit-app-template.git
```

#### 1b. Navigate to Cloned Directory (linux only)

```bash
cd kit-app-template
```

### 2. Create and Configure New Application From Template

Run the following command to initiate the configuration wizard:

**Linux (bash):**
```bash
./repo.sh template new
```

**Windows (open powershell in cloned directory):**
```powershell
.\repo.bat template new
```

> **Note:** If this is your first time running the `template new` tool, you'll be prompted to accept the Omniverse Licensing Terms.

Follow the prompt instructions
( *feel free to use default values if you are just trying it out )*:
- **? Select with arrow keys what you want to create:** Application
- **? Select with arrow keys your desired template:** USD Viewer
- **? Enter name of application .kit file [name-spaced, lowercase, alphanumeric]:** [set application name]
- **? Enter application_display_name:** [set application display name]
- **? Enter version:**: [set application version]

If selected template requires a setup extension:
- **? Enter name of extension [name-spaced, lowercase, alphanumeric]:** [set extension name]
- **? Enter extension_display_name:** [set extension display name]
- **? Enter version:** [set extension version]


### 3. Build

Build your new application with the following command:

**Linux:**
```bash
./repo.sh build
```
**Windows:**
```powershell
.\repo.bat build
 ```

 If you experience issues related to build, please see the [Usage and Troubleshooting](readme-assets/additional-docs/usage_and_troubleshooting.md) section for additional information.


### 4. Launch

Initiate your newly created application using:

**Linux:**
```bash
./repo.sh launch
```
**Windows:**
```powershell
.\repo.bat launch
```

**? Select with arrow keys which App would you like to launch:** [Select the created viewer application]

***NOTE:* Initial startup may take a few extra minutes as shaders compile. The application should present as a black screen when ready.**

## Complimentary Examples (optional)
- [Containerize Viewer](readme-assets/additional-docs/viewer-container.md) to run on a remote kubernetes cluster.

## Tools

The `kit-app-template` includes a suite of tools to aid in the development, testing, and deployment of your projects. A brief overview of some key tools:

- **Help (`./repo.sh -h` or `.\repo.bat -h`):** Provides a list of available tools and their descriptions.

- **Template Creation (`./repo.sh template` or `.\repo.bat template`):** Assists in starting a new project by generating a scaffold from a template application or extension.

- **Build (`./repo.sh build` or `.\repo.bat build`):** Compiles your applications and extensions, preparing them for launch.

- **Launch (`./repo.sh launch`or`.\repo.bat launch`):** Starts your compiled application or extension.

- **Testing (`./repo.sh test` or `.\repo.bat test`):** Facilitates the execution of test suites for your extensions, ensuring code quality and functionality.

- **Packaging (`./repo.sh package` or `.\repo.bat package`):** Aids in packaging your application for distribution, making it easier to share or deploy in cloud environments.


For a more detailed overview of available tooling see the [Kit App Template Tooling Guide](readme-assets/additional-docs/kit_app_template_tooling_guide.md) or execute the help command specific to the tool your are interested in (e.g. `./repo.sh template -h` or `.\repo.bat template -h`).

## Template Docs

- [USD Viewer](readme-assets/additional-docs/usd_viewer_template.md)

## License

Development using the Omniverse Kit SDK is subject to the licensing terms detailed [here](https://docs.omniverse.nvidia.com/install-guide/latest/common/NVIDIA_Omniverse_License_Agreement.html).

## Additional Resources

- [Usage and Troubleshooting](readme-assets/additional-docs/usage_and_troubleshooting.md)

- [BETA - Developer Bundle Extensions](readme-assets/additional-docs/developer_bundle_extensions.md)

- [Omniverse Kit SDK Manual](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/index.html)


## Contributing

We provide this source code as-is and are currently not accepting outside contributions.