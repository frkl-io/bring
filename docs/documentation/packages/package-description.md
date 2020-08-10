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

## section: '*source*'

A packacke description *must* have a section with the key ``source``. Ideally, it describes a package in a way that is idempotent, which means that, if given the same input values, it'll always yield the exact same files, in the exact same folder structure. In some cases that is not possible/required, but we'll ignore that for now and assume idempotency.

The *source* section itself can be split up into 3 different sub-sections:

**type** (required)
:    the name of the [package type](/documentation/packages/package-types) plugin that will read and process this data. *bring* supports multiple such package types, to accomodate for the different ways people publish their files.

**type-specific keys** (almost always required)
:    echo package type has different required and optional arguments. Check their respective documentation for details.

**common keys** (optional)
:    *bring* uses *package-type plugins* to retrieve source files for packages, but then uses the same code to post-process those files. This code also can take some input in order to costumize the final structure of a package.

### key: *type*

Currently available, official package types are:

{% for pkg_type, expl in pkg_types.items() %}
{% if pkg_type != "folder" %}- [``{{ pkg_type }}``](/documentation/packages/package-types#type-{{ pkg_type }}): {{ expl.explanation_data["doc"].get_short_help(list_item_format=True) }}
{% endif %}{% endfor %}

### *type-specific keys*

Those differ for each package type. Check the documentation of the type you intend to use for details.

### *common keys*

Those keys are currently supported:

``aliases`` (optional)
:    A dictionary with the variable names as keys, and an alias dictionary (with alias as key, and final value as, well, ...value).

    E.g., for:

    ``` yaml
    os:
      linux: unknown-linux-gnu
      darwin: apple-darwin
    ```

    ...an input value of ``linux`` for the ``os`` variable would resolve to ``unknown-linux-gnu``. Package types sometimes provider their own aliases (for example 'latest' as a pointer to the latest version of a github release).

``args`` (optional)
:  

``artefact`` (optional)
:    An optional argument that specifies the type of source package artefact for a package (which could be a tar.gz- or zip-archive, a folder, a single-file, etc.). Internally, ``bring`` requires each package to be a folder containing one or several files. This argument helps transform single-file artefacts (archive, normal file) into
a folder (for example by extracting it, or move a single downloaded file into a newly created temporary folder). In most cases, you won't need to specify it. For the cases where that is not true, those values are currently supported:

    - ``file`` - a plain, single file
    - ``folder`` - a folder (for example when the artefact is a git repository)
    - ``archive`` - an archive file (currently supported archive types: zip, tar, tar.gz, tar.bz2, xtar)

    If ``artefact`` is not specified, the default mechanism of a specific package type is used (which should work for most cases).


## section: *metadata*

### key: *info*

### key: *tags*

### key: *labels*
