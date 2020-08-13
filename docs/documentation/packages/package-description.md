A package description is composed of two parts:

the package  ***source*** (required)
:     a data structure that describes where to retrieve the files of a package, and how to assemble them (e.g. whether to rename some files, make some of them executable, etc.)

additional package ***metadata*** (optional)
:     other, optional metadata (like the author/publisher of the file, a homepage, labels, tags...)

## Example

To get an idea how a full, 'working' package description looks like, here's one that lets you install the [pandoc](https://pandoc.org/) binary, an application to convert between document formats:

``` yaml
{{ pandoc_details["full"] | to_yaml }}
```

You can use the ``explain`` subcommand to debug a package, and print out the data it collects:

{{ cli_html("bring", "explain", "pkg", "binaries.pandoc", max_height=240, fake_command="bring explain pkg [path_to_pandoc_desc_file].pkg.br") }}

## section: '``source``'

A packacke description *must* have a section with the key ``source``. Ideally, it describes a package in a way that is idempotent, which means that, if given the same input values, it'll always yield the exact same files, in the exact same folder structure. In some cases that is not possible/required, but we'll ignore that for now and assume idempotency.

The *source* section itself can be split up into 3 different sub-sections:


### key: '``type``'

The name of the [package type](/documentation/packages/package-types) plugin that will read and process this data. *bring* supports multiple such package types, to accomodate for the different ways people publish their files.
Currently available, official package types are:

{% for pkg_type, expl in pkg_types.items() %}
{% if pkg_type != "folder" %}- [``{{ pkg_type }}``](/documentation/packages/package-types#type-{{ pkg_type }}): {{ expl.explanation_data["doc"].get_short_help(list_item_format=True) }}
{% endif %}{% endfor %}

### *type-specific keys*

Each package type has different required and optional arguments. Check their respective documentation for details.

### *common keys (optional)*

*bring* uses *package-type plugins* to retrieve source files for packages, but then uses the same code to post-process those files. This code also can take some input in order to costumize the final structure of a package.

Those keys are currently supported:

#### ``aliases``

A dictionary with the variable names as keys, and an alias dictionary (with alias as key, and final value as, well, ...value).

E.g., for:

``` yaml
os:
  linux: unknown-linux-gnu
  darwin: apple-darwin
```

...an input value of ``linux`` for the ``os`` variable would resolve to ``unknown-linux-gnu``. Package types sometimes provider their own aliases (for example 'latest' as a pointer to the latest version of a github release).

#### ``args``

A dictionary to let you control how package arguments are presented to the user. *bring* comes with default argument configurations for 3 argument keys: ``version``, ``arch``, ``os``. If your package has other input variables (or if you want to override the defaults), you can do that here.

Here is a list of available configuration keys (all of them optional):

- **``doc``**: a string describing the argument
- **``type``**: the type of the argument. supported: "any", "string", "integer", "list", "dict", "boolean" (and a few others, to be documented later -- defaults to "any")
- **``default``**: a default value if none is provided for the (no default)
- **``required``**: whether the argument is required or optional (defaults to 'true')
- **``multiple``**: whether a only a single, or multiple values are allowed (defaults to 'false')
- **``allowed``**: a list of allowed values (not implemented yet -- no default)

As an example for the: the [``kubernetes.ingress``](https://gitlab.com/bring-indexes/kubernetes/-/blob/master/ingress-nginx.pkg.br) requires an extra ``provider`` argument, to determine the exact yaml manifest file to select. This variable is described with data like:

```yaml
args:
  provider:
    doc: The provider to deploy to.
    default: cloud
```

This will change the output of the package install help command to be:

{{ cli("bring", "install", "kubernetes.ingress-nginx", "--help") }}

And it will use ``cloud`` as value for that key if not specified otherwise by the user.


####``artefact``
 An optional hint to specify the type of source package artefact for a package (which could be a tar.gz- or zip-archive, a folder, a single-file, etc.). Internally, ``bring`` requires each package to be a folder containing one or several files. This argument helps transform single-file artefacts (archive, normal file) into
a folder (for example by extracting it, or move a single downloaded file into a newly created temporary folder). In most cases, you won't need to specify it. For the cases where that is not true, those values are currently supported:

- ``file`` - a plain, single file
- ``folder`` - a folder (for example when the artefact is a git repository)
- ``archive`` - an archive file (currently supported archive types: zip, tar, tar.gz, tar.bz2, xtar)

If ``artefact`` is not specified, a semi-smart detection mechanism is used (which should work for most cases).

#### ``transform``

Optional configuration to control which files that are contained in the original artefact will end up in the package. This is the most used configuration option, as often you are not interested in supplementary files (licenses, configuration examples, etc.) to be installed into the target.

Configuration for this value is done via providing a list of items as input. Each item can either be a string (for simple filtering), or a dictionary of values (if more advanced configuration is necessary).

If no value for ``transform`` is provided, all files of the package will be copied into the target. If one or several list items are set, only those will be used, and all non-matching files will be ignored.

If a list item is a string, the full path to that file is looked up in the source package folder, and copied over to the target using the exact same path/filename. If a dictionary is provided, those are the available configuration keys:

- **``from``** (required string): the path to the file/the filename in the source
- **``to``** (optional string): the target path/filename (defaults to the value of ``from``)
- **``mode``** (optional, string or integeer): the permissions of the file on the target (e.g. '0755', 644, ...)

All variables that are used to resolve a version of a package are allowed in variable placeholders (``${var_name}``).

An full example from the [binaries.k3d](https://gitlab.com/bring-indexes/binaries/-/blob/master/virtualization/orchestration/kubernetes/k3d.pkg.br) package, which renames an os-specificly named file to a more generic name, and also makes the file executable:

```yaml
transform:
  - path: k3d
    from: "k3d-${ os }-amd64"
    mode: 755
```  

Other configuration keys are not supported currently, neither is selecting files via globs/regexs. There are plans to do that in the future though. Mixing string and dictionary items is allowed.  

## metadata sections:

### section: '``info``'

Contains information about the package itself, the most important sub-keys are: ``slug`` (description of the package), ``homepage``.

### section: "``tags``"

A list of strings containing tags that apply to the package. This is not used at the moment, but will be later to filter/select packages.

### section: "``labels``"

A list of strings containing labels that apply to the package. This is not used at the moment, but will be later to filter/select packages.
