<img src="./docs/Images/pulse_logo_512.png" alt="Pulse Physiology Engine" width="256" height="106">

The Pulse Physiology engine is a C++ based simulation engine for human and animal physiology.
It is intended to provide accurate and consistent physiology data to medical education, research, and training technologies. 
The built libraries are static and can be integrated with standalone applications, hardware simulators, sensor interfaces, and other physiology models of all fidelities.

Along with the build instructions below, we provide more technical discussions using Pulse on our <a href="https://gitlab.kitware.com/physiology/engine/wikis/home">wiki</a>

For detailed information about our design and methodology read our <a href="https://physiology.kitware.com/">documentation</a>

Use this <a href="https://discourse.kitware.com/c/pulse-physiology-engine">discourse channel</a> 
to ask or share anything and everything about building, using, or understanding the Pulse engine and welcome to our community!!

## Checkout

Pulse branching convention:

- **Stable:** This branch is fully validated and tested. We recommend using this branch when using Pulse in your applications or studies.
- **Integration:** This branch is generally stable, but not validated. It is the bleeding edge of our current feature development. As new features are completed they are merged into the integration branch. This branch allows us to understand how different models interact with each other. We often find unexpected consequences when code from multiple features we are developing are merged together. We address these issues as quickly as possible. Once they all integration issues are addressed we need then have to assess the validation of all models before merging into our stable branch. Validation is currently a manual process and can delay merging into stable. 
- **Features:** Branches starting with `feature/` are self contained updates for a particular addition to the code. It is not recommended to pull these branches unless you are helping to develop this feature.

## Build Environment

The code provided utilizes C++17, here is a list of popular compilers and their initial version to implement all of C++17 :

- GCC 9 and later
  - While GCC 7/8 have C++17 support, it was still experimental and requires different includes/linkages
- Clang 5 and later
- MSVC 2017 and later

While the provided cmake superbuild automatically pulls many libraries it needs to compile, 
you will still need to have the following tools installed (along with your choice of C++ compiler) :

### CMake
Currently, the code requires CMake 3.12 or greater to properly build
Go to the cmake website, <a href="https://cmake.org/download">https://cmake.org/download</a>, and download the appropriate distribution.
Ensure that cmake bin is on your PATH and available in your cmd/bash shell.

#### On Linux

If you are on a Debian/Ubuntu system, please install the latest cmake on your system by <a href="https://apt.kitware.com/">following thes instructions</a>.

### Python Dependency

By default, the Pulse_PYTHON_API CMake option is enabled.
Some of our test suite and data generate tools used are written in Python.
While there is no dependency on Python when integrating with your application, it is strongly recommended enable Pulse_PYTHON_API when building Pulse to develop/contribute to the code base.
If you are building Pulse strictly to generate native binaries, you can disable this CMake option.

Simply <a href="https://www.python.org/downloads/">download and install python</a> and ensure that it is available on your path.

Next, install the required python packages via our requirements.txt file at the root of the code base

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# Install python packages used by Pulse
$ pip3 install -r <path/to/pulse/source/>requirements.txt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

### Java JDK

By default, the Pulse_JAVA_API CMake option is enabled.
Some of our test suite and data generate tools used are written in Java.
While there is no dependency on Java when integrating with your application, it is strongly recommended enable Pulse_JAVA_API when building Pulse to develop/contribute to the code base.
If you are building Pulse strictly to generate native binaries, you can disable this CMake option.

A JAVA_HOME environment variable needs to exist pointing to the Java installation.<br>
There are many ways to do this.
We recomend using the Amazon Corretto JDK 8

Follow the installation instructions for your operating system <a href="https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/what-is-corretto-8.html">here.</a>

#### Windows

To set a global JAVA_HOME environment variable pointing to the Java installation:

- Download the Windows x64 JDK <a href="https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/downloads-list.html">here.</a>
- Run the installer for Win.
- Goto your Control Panel->System and click Advanced system settings on the left. <br>
- Click the 'Environment Variables' button and add JAVA_HOME as a new 'System variables'.<br>
- Set the Value to something like: N:/Programming/Tools/jdk1.8.0_212<br>
    - It's a good idea to add the JDK to the system PATH by adding this to the beginning: %JAVA_HOME%/bin;
- Make sure to start a new cmd window.<br>

#### Mac

Use the <a href="https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/macos-install.html"> instructions provided by amazon. </a> 

#### Linux

Use the <a href="https://docs.aws.amazon.com/corretto/latest/corretto-8-ug/generic-linux-install.html"> instructions provided by amazon. </a> 

If you would like to use the open jdk, follow these instructions:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# Check to see if you have the JDK
$ update-alternatives --list java
# Note: Make sure you don't add the jre in the path of the java listed
# for example you may see '/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java'
# you will want the truncated '/usr/lib/jvm/java-8-openjdk-amd64'
# If you do not have the Java SDK
$ sudo apt-get install openjdk-8-jdk
# Set the JAVA_HOME environment variable
# NOTE your Java path may vary!
# Use the update-alternatives to find your system's Java path
export JAVA_HOME='/usr/lib/jvm/java-8-openjdk-amd64'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also add it to your ~/.bash_profile, or related file (.bashrc, .zshrc, .cshrc, setenv.sh), to get the path in all shells.

### C Sharp Dependency

When building with the Pulse_CSHARP_API option, you will need to ensure you have the latest version of the <a href="https://dotnet.microsoft.com/en-us/download">.NET 6 SDK</a> installed.


## Building

The build is directed by CMake to ensure it can be built on various platforms. 
The code is build by a CMake 'superbuild', meaning as part of the build, CMake will download any
dependent libraries and compile those before it builds. 
The build is also out of source, meaning the code base is seperated from the build files.
This means you will need two folders, one for the source code and one for the build files.
Generally, I create a single directory to house these two folders.

Visual Studio users, our <a href="https://gitlab.kitware.com/physiology/engine/wikis/Using%20MSVC">wiki provides detailed steps for building with MSVC</a>

Here is the quickest way to pull and build via a bash shell:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
$ mkdir Pulse
$ cd Pulse
$ git clone https://gitlab.kitware.com/physiology/engine
# This will put the source in an 'engine' folder
$ mkdir builds
$ cd builds
# Feel free to make subfolders here, like debug or release
# Generate a make file solution for the external dependencies
# Note you need to provide cmake the source directory at the end (relative or absolute)
# Run CMake (it will use the system default compiler if you don't provide options or use the CMake GUI)
$ cmake -DCMAKE_BUILD_TYPE:STRING=Release ../engine
# If you want the build to pull the Verification and Validation (V&V) scenarios and baselines run this (or check the Pulse_DOWNLOAD_BASELINES option in the CMake GUI)
# You can always pull these later if you want (See Running and Testing)
$ cmake -DCMAKE_BUILD_TYPE:STRING=Release -DPulse_DOWNLOAD_BASELINES:BOOL=ON ../engine
#
# Build the install target/project
# On Linux/OSX/MinGW 
$ make -j4
# cd into the 'Pulse' directory for building any changes specific to the Pulse code base
# Such as if you pull new Pulse code or make changes, run make from the Pulse directory
# See below for more details in pulling and rebuilding
$ cd Pulse
# To run Pulse, cd to the install/bin directory
$ cd install/bin
# In this example that would be ~/Pulse/builds/install/bin
# Now you can run something
$ ./PulseScenarioDriver VitalsMonitor.json
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

### Docker Support

Pulse provides a docker file that, by default, builds a linux based docker container with Python support.

To build this docker container, pull the source code and run the docker build command from the source root.
Kitware provides Pulse containers on [dockerhub](https://hub.docker.com/r/kitware/pulse).

Here is an example of building a docker container and pushing it to an organization repository in dockerhub:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# From the Pulse source directory
$ docker build -t kitware/pulse:3.0.0 .
$ docker push kitware/pulse:3.0.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

### Single Board Computers Support 

Note that on small boards, like the Beagle Board Black and DragonBoard 410c, you may need to allocate a <a href="https://www.cyberciti.biz/faq/linux-add-a-swap-file-howto/">temporary swap</a> file if your build runs out of memory

It boils down to:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
su - root
fallocate -l 1G tmpswap
mkswap tmpswap
swapon tmpswap
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Read the article if you want to make this change permanent, it contains some valuable hints regarding permissions and fstab.
### Cross Compiling

CMake provides the ability to easily cross compile.
In general, when we cross compile, we are doing so to get out a PulseC library.
The PulseC library provides an interface used by our C#/Unity and Python API's to access and control the C++ based engine.
Unity is C# based and any C# managed libraries built on any platform, will automatically run on other platforms.
But the PulseC library is a native library and a specific platform version must be provided for the platform Pulse is being run on.
The following sections will highlight specific build instructions for cross compiling for these target platforms.

#### Native Platform Build

The first thing you will want to do is build Pulse on the host system. I use Visual Studio when building natively.
During the Pulse build, it will build and run the Protobuf protoc compiler to generate C++ classes needed for I/O.
These files are needed to build, but when you cross compile, you will build a protoc executable for your target platform, and it will not run on the native host system.
Doing a native build will ensure these files are generated. The cross compile build will see the files exist and not run the non native protoc compiler.
Once you have a native build, create a new empty build directory for your cross compile build.

#### Dockcross

To generate Pulse libraries for android, linux, and web assembly, we use docker containers provided by [dockcross](https://hub.docker.com/u/dockcross). Dockcross provides both a build environment and a cmake toolchain file that simplifies the cross platform build process. 
Simply pull the target docker container, run cmake, and build.
I am using docker on windows via the WSL 2 based engine, from an [Ubuntu 20](https://www.microsoft.com/en-us/p/ubuntu-2004-lts/9n6svws3rx71?activetab=pivot:overviewtab) terminal.

Here is an example bulding Pulse for Android armv8a.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# Run this command from a directory that contains both your sourc and your build directories
$ docker run --rm dockcross/android-arm64 > ./armv8a
# This creates a file we will use to invoke our container
# Next, set execution permissions
$ chmod +x ./armv8a  
# Run CMake
# -B is the relative path to my build directory
# -H is the relative path to my Pulse source directory
$ ./armv8a cmake -DPulse_JAVA_API:BOOL=OFF -B./Builds/pulse-engine-armv8a -H./Pulse/engine -GNinja
# Use ninja to build (provided in the docker)
$ ./armv8a ninja -C./Builds/pulse-engine-armv8a
# The PulseC.so for the target platform will be in the pulse-engine-armv8a/install/bin directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#### Dockcross compile scripts

To make cross compiling with dockcross easier, we have provided batch script file for both windows and *nix operating systems.

This script will create a `dockcross-builds` directory one level up from your Pulse source directory.
A build directory for each platform will be created within this directory.
Platforms are specified in the xcompile.bat and xcompile.sh scripts.
We currently use these scripts to build a linux distribution independent and android arm7 and arm8 based PulseC.so binaries.
You can modify these files to build the desired platform.
These scripts encapsulate the commands descibed above.
To start these builds simply open a terminal in the Pulse source directory and start the script

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# Build various platform targets
$ ./xcompile.sh
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PulseC binaries are located in each platform/install/bin directory

#### iOS

iOS can only link to static iOS arm64 C++ Pulse libraries. 
We have not yet added support to our build system to build these via the terminal.
We build these manually on a MacOS machine using XCode.
The following steps are used to generate these static libraries for our Unity Asset.

1. Since we are cross compiling, non of our executables are able to run on our MacOS machine. This include the protoc compiler.
Inorder to generate the necessary files during the build process, you will need to build Pulse for the native MacOS platform.
Simply follow the above build instructions. We will refer to its build directory as `macos/install` in subsequent steps.
2. Open CMake and <b>configure</b> an XCode project with a <B>toolchain file for cross compiling</b>. Use the toolchain file `/cmake/ios.toolchain.cmake`
3. Set Pulse_NATIVE_BUILD_DIR to your `macos` root build directory 
4. Ensure Pulse_C_AS_STATIC is set to `ON` so we only build the necessary static libraries
5. Ensure `Pulse_JAVA_API` and `Pulse_PYTHON_API` are set to `OFF`
6. Configure and Generate CMake for it to create the XCode project


#### Magic Leap

Magic Leap provides a Lumin SDK for use in compiling native C++ code for use on the Magic Leap platform.
You will need to download and install this SDK. 
In this example we are building on a windows machine, using the Lumin SDK v0.24.1.
Please follow the [Lumin instructions on generating a cmake toolchain file](https://developer.magicleap.com/en-us/learn/guides/sdk-mabu-ref-build-and-link-libraries#build-libraries-with-cmake) needed for cross compiling.

I had to modify the toolchain file, adding '-llog' for protobuf's use of the android log methods, as well as '-g -std=c++11 -Wall -pedantic' to add C++11 support.
`set(CMAKE_CXX_FLAGS "-g -std=c++1z -Wall -pedantic ` <br>
`set(CMAKE_EXE_LINKER_FLAGS "-llog ` <br>
`set(CMAKE_SHARED_LINKER_FLAGS "-llog ` <br>

Here is a copy of the [modified toolchain file](https://data.kitware.com/api/v1/file/5f29b9489014a6d84e57067a/download)

To generate a Makefile and build, run :

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# Where -H specifies the Pulse source, and -B is the build directory
cmake -DPulse_JAVA_API:BOOL=OFF -DCMAKE_TOOLCHAIN_FILE:FILEPATH=C:/Programming/magicleap.0.24.1.toolchain.cmake -BC:/Programming/Builds/pulse-engine-lumin -HC:/Programming/Pulse/engine -G "Unix Makefiles"

# Run make from within your build directory
N:/Tools/MagicLeap/dev/mlsdk/v0.24.1/tools/mabu/tools/MinGW/bin/mingw32-make.exe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This will provide a PulseC.so in the build/install/bin that works on the Magic Leap platform!

## Executing Pulse

We provide a set of scripts to assist in the development of Pulse.
These scripts call fuctionality implented in both Java and Python.
This repository contains all reqired Java jar files, we only require that Java is discoverable on your Path.
However Python based functionality requires that Python is discoverable on your Path _and_ your Python environment has pip installed the packages in our requirements.txt

## Updating Pulse

The Pulse repository is always changing as we add improvements and features to the code base.
These changes will require that you rebuild the source code when you pull the latest changes.
Here are a few tips for keeping your source code up to date when you pull:

<b>Please ensure CMake is on your path!</b>

### Rebuilding the schema

Pulse uses Google Protocol Buffers for data files and to communicate data between various languages and networking protocols.
After you pull the latest, you will need to run the Protoc compiler to adjust the data model to any changes made to the proto files describing the Pulse Data Model.

From a command/terminal in your pulse/build/install/bin directory : 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# On Windows
> run protoc
# On Linux/Mac
$ ./run.sh protoc
# Note you may need to do a 
$ chmod +x run.sh
# To run this script on your machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note: If there were no changes to the protobuf files, the proto compile will not run and return this message 

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
-- Not generating bindings, nothing has changed since last build
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are getting linking errors about missing protobuf functions,
such as missing something in the cdm:: namespace,
you can force the protoc compiler to run by deleting this timestamp file:

<b>pulse/build/Pulse/schema/schema_last_built</b>

### Rebuild the code base

With the Protocol Buffer bindings updated, you can now build the updated code base.

### Regenerate State Data

Any changes to the code base can change various aspects of the data our engine calculates.
This in-turn has can have an effect on the various state files used in our HowTo examples
(located in the pulse/install/bin/states directory).
If the state files no longer load, or you want to ensure they are up to date with your version of the engine code, regenerate these state files:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# On Windows
> run genStates
# On Linux/Mac
$ ./run.sh genStates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

### Update Baseline Data

Changes to the code base can also change the Test Suite baseline files.
You will need these new baseline files to pass any tests and ensure any changes do not affect the code base in any negative ways.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~bash
# On Windows
> run updateBaselines
# On Linux/Mac
$ ./run.sh updateBaselines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

## Using Pulse

With the code built, visit our [wiki](https://gitlab.kitware.com/physiology/engine/wikis/home) to learn how to execute Pulse and use our SDK to use Pulse in your own application with Pulse.

