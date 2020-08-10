### List default indexes

To quickly get a list of available indexes and packages, use the ``list`` sub-command:

<div class="code-max-height">
{{ cli("bring", "list", max_height=400) }}
</div>

### Display information

In order to get more information about an index or package, you can use the ``explain`` sub-command. Use either ``index`` or ``package`` as first argument, and the name of the index or package as second.

#### Index metadata

This is how to get metadata for the ``binaries`` index:

{{ cli_html("bring", "explain", "index", "binaries", max_height=400) }}

#### Package metadata

And this is how to get the details for the ``fd`` package that is a part of the ``binaries`` index:

{{ cli_html("bring", "explain", "package", "binaries.fd", max_height=400) }}
