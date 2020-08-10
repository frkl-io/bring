A package description is composed of two parts:

**the package  '*source*' ** (required)
:     a data structure that describes where to retrieve the files of a package, and how to assemble them (e.g. whether to rename some files, make some of them executable, etc.)

**package *metadata* ** (optional)
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

``artefact`` (optional)
:    describes the type of the


## section: *metadata*

### key: *info*

### key: *tags*

### key: *labels*
