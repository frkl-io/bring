# Indexes

## Definition

A *bring* index is a collection of [packages](/documentation/packages/overview).

Each index has a (namespaced) unique name (e.g. ``gitlab.bring-indexes.binaries``); some of the indexes that ship with *bring* are
non-namespaced aliases for a fully-namespaced index names (``binaries``, in this case).

Each package in a *bring* index is referred to by a unique (within that index) name. That package name can't contain '.'-characters. That means, *bring* can resolve every namespaced string like ``gitlab.bring-indexes.binaries.fd`` (or its alias ``binaries.fd``) into a globally unique *bring* package.

## Creating an index

 There are different ways to create an index, but the main one is to just have a folder (in most cases: a remote git repository) containing [bring package description](/documentation/packages/package-description) files. Those files are basically text files with a ``.pkg.br``-extension, containing a [YAML](https://yaml.org/) document. Check the **binary** index to see how such a directory could look like: https://gitlab.com/bring-indexes/binaries

Packages names are derived from the description file name (without the ``.pkg.br`` extension), and an index should never contain the same package name more than once (even if they are located in different subfolders), as that can lead to errors or unpredictable outcomes.

## Exporting index data

As parsing a local or remote folder structure can become slow once such a folder contains a lot of files, it is also possible to 'export'
all the package data contained in an index into a single index file. The command for that is:

{{ cli_html("bring", "export-index", project_root + "/docs/examples", fake_command="bring export-index [path-to-index-folder]") }}

This will create a file ``[path-to-index-folder]/.bring/this.idx.br``, which is a gzipped json file with a snapshot of all the resolved
package data of this index. If such a file exists, *bring* will use that instead of parsing a folder/repository.

In addition to not having to parse a folder structure anymore, this also makes package version lookups faster, since all the
version information is 'frozen' within such an index file. The one disadvantage is that package data is more likely to be out of date than a 'freshly' parsed index folder. This is not always the case though, since *bring* also caches package version information locally, after the first lookup, which means that issuing a ``bring update`` every now and then is advisable.

TODO: explain consistency check/index updates
