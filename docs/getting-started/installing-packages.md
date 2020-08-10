## Install a package

When you don't need a specific version of a package, you can install a package...

### ... using only default values

To install one of the available packages without any customization, all you need to do is specify the full name for the package:

{{ cli_html("bring", "install", "binaries.fd") }}

*bring* always tries be as clear as possible as to what it is doing, which is why it prints the values it ends up using, as well as their origin.

For example, as you can see from the output of that command, the ``fd`` binary file was installed into the local ``$HOME/.local/bring`` folder. This is because that is the default folder for the ``binaries`` *index* (check the ['explain' command documentation](/getting-started/information/#display-information) on how to get that information). In addition to the ``target`` default, that index also comes with a set of auto-generated default values that describe the OS and architecture of the system *bring* is running on (which is helpful to pick the right version of a binary, for example).

In some cases the default target might not be suitable for you though. In that case, you can install the package...

### ... into a specific folder

If you need to install a package into a specific directory, use the ``--target`` parameter:

{{ cli_html("bring", "install", "--target", "/tmp/bring", "binaries.fd", start_lines=13, end_lines=5) }}

The target folder, as well as any intermediate ones, will be created in case they don't exist yet.

If you don't specify the ``--target`` parameter, and the index does not have a default target set, the files will be copied into a temporary directory somewhere under `~/.local/share/bring/workspace/results/`:

{{ cli_html("bring", "install", "kubernetes.cert-manager", start_lines=1, end_lines=5) }}

To have more fine-grained control of the version of the package to install, you have to use the *install* command...

### ... with arguments

Packages often come in different flavours (e.g. which architecture, OS, etc.), as well as several versions, which can be specified in the ``install`` command after the package name. Depending on the *index* configuration, ``bring`` assumes certain default values which often make it so that no package arguments at all need to be provided.

But, often it is advisable to specify the exact version of a package to install. If that is desired, you can use the ``--help`` parameter (after the package name) to get ``bring`` to display information about the supported arguments:

{{ cli("bring", "install", "binaries.fd", "--help") }}

To check which values are allowed, the ``explain`` subcommand is often useful (like the one we used [here](/getting-started/information#package-metadata)).

To illustrate, the following is an example showing how to specifically install version '7.1.0' of the Mac OS X variant of ``fd``:

{{ cli_html("bring", "install", "binaries.fd", "--version", "7.1.0", "--os", "darwin", start_lines=11, end_lines=5) }}

## Install details

In case you are wondering what the install command actually does, you can use the ``--explain`` flag to get some information about the variables used, and the steps that are executed during the install process (without actually doing anything):

{{ cli_html("bring", "install", "--explain", "binaries.fd", "--os", "darwin") }}
