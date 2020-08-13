This guide walks you through the creation of your first *bring* package. For details about the package description format, available package types and other more in-depth in formation check out the [package description documentation](/documentation/packages/package-description).

## Create the package description file


For this example, we'll create a package for one of the files in [this example git repository](https://gitlab.com/bring-indexes/example-source-repo), specifically [this file](https://gitlab.com/bring-indexes/example-source-repo/-/blob/master/some-files/file1.md).

Since the file we are interested in is hosted on Gitlab, and we only are interested in this particular file and not the whole repository, we will use the [``gitlab_files``](/documentation/packages/package-types/#type-gitlab_files) package type.

### ...using the ``create pkg-desc`` sub-command

*bring* [package types](/documentation/packages/package-types) come with some helpers to make it easier to create package descriptions by auto-filling in some required and/or default values.

Without any arguments (apart from the required package type name), ``bring create pkg-desc [package-type]`` will return a bare package description string, which you can use as a starting point by copying it into a file and filling in some required values:

{{ cli_html("bring", "create", "pkg-desc", "gitlab_files", max_height=340) }}

We can also tell *bring* to create the package description file straight away:

{{ cli_html("bring", "create", "pkg-desc", "gitlab_files", "-f", "example-file1", max_height=340) }}

*Note*: if no file extension is provided, *bring* will use the default '``.pkg.br``'

We can now go through that file, and fill in the 3 required values for the ``gitlab_files`` package type:

- **``user_name``**: in our case ``bring-indexes``
- **``repo_name``**: here we use ``example-source-repo``
- ** ``files``**: we only want one file, so we use a single-item list: ``['some-files/file1.md']``

Once that is done, we can use the ``explain`` sub-command to get the details of our newly create package:

{{ cli_html("bring", "explain", "package", project_root + "/docs/examples/example_file1.pkg.br", fake_command="bring explain package example_file1.pkg.br") }}

As you can see in that output, *bring* determined the available versions, and selected an appropriate alias for the latest tag.

We could now comment out some of the metadata fields and fill in some of the values manually. Or we could be...

### ...using the ``create pkg-desc`` command with arguments

Some package type plugins support auto-filling some of the metadata (and other) values of a package description, given enough basic information.

For the ``gitlab_files`` plugin we can find out which values are required by issuing:

{{ cli("bring", "create", "pkg-desc", "gitlab_files", "--help") }}

Let's try that:

{{ cli_html("bring", "create", "pkg-desc", "gitlab_files", "--user-name", "bring-indexes", "--repo-name", "example-source-repo", "--files", "some-file/file1.md") }}

As with the example above, we can use a file-path argument at the end of this command to write this description to a file straight away. This description should be usable without any further manual editing, since we provided all required values via the command-line. Plus, *bring* added some of the metadata in 'info' automatically (which we could change, if we don't like it).
