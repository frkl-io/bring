A package description is composed of two parts:

**the package  '*source*' ** (required)
:     a data structure that describes where to retrieve the files of a package, and how to assemble them (e.g. whether to rename some files, make some of them executable, etc.)

**package *metadata* ** (optional)
:     other, optional metadata (like the author/publisher of the file, a homepage, labels, tags...)

## Example

Before explaining in detail how each of the sections of a package description works, here's a look of a 'working' package description which contains the [pandoc](https://pandoc.org/) binary:

``` yaml
{{ pandoc_details["full"] | to_yaml }}
```

## '*source*' section

The *source* section of a package description

## *metadata*
