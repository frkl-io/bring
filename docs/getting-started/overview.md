### Information/Help

 - [Getting information](/getting-started/information): how to retrieve information about packages, indexes, and other items of interest

### Packages

A *bring* package is metadata that describes how to get a specific version of a file or set of files onto your machine; those files are usually remote, and not managed by yourself.

 - [Installing packages](/getting-started/installing-packages): how to install a *bring* package
 - [Creating a package](/getting-started/creating-packages): how to create *bring* package descriptions

### Indexes

An index is a collection that contains packages. It has a (namespaced) unique name; within an index packages are referred to by name. Thus, each package can be addressed by a single string of the format ``<index_name>.<package_name>``, e.g.: ``binaries.fd``, ``gitlab.bring-indexes.example-index.pandoc``, ...
