Before getting started with *bring*, it is important to understand two concepts:

**package**
:    A *bring* package is metadata that describes how to get a specific version of a file or set of files onto your machine; those files are usually remote, and not managed by yourself.

**index**
:    An index is a collection that contains packages. It has a (namespaced) unique name; within an index packages are referred to by name. Thus, each package can be addressed by a single string of the format ``<index_name>.<package_name>``, e.g.: ``binaries.fd``, ``gitlab.bring-indexes.example-index.pandoc``, ...

## Topics

 - [Getting information](/getting-started/information): how to retrieve information about packages, indexes, and other items of interest
 - [Installing packages](/getting-started/installing-packages): how to install a *bring* package
