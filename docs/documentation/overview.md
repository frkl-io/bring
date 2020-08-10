---
title: bring documentation overview
nav: false
---

## Concepts

The purpose of `bring` is to copy files and file-sets onto the local system, in a reliable, replicable way. The three main concepts to understand in regards to `bring` are:


**[package](/documentation/packages/overview)**
:    A *package* is a specific file or file-set, usually versioned in some way (via git, releases, etc.). In most cases, a package is uniquely identified by an index name (see below) and the package name as the right-most part of the string: ``[index.name.space].[package_name]``, e.g. ``gitlab.tingistries.binaries``.

**[indexes](/documentation/indexes/overview)**
:    An *index* is a list that contains metadata for one or several *packages*, usually of one category (single-file binaries, templates, etc...) or otherwise belonging together.  
  Indexes can be of different types, the most common ones will be pointing to git repositories on GitLab/GitHub/etc in the form of ``[service_name.user_name.repo_name]``, e.g. ``gitlab.tingistries.binaries``. In addition, the *indexes* that are included in ``bring`` usually have single-name aliases (e.g. ``binaries``).

**[contexts](/documentation/configuration/overview)**
:    Sets of indexes and other configuration values are managed within so-called *contexts*; by default `bring` uses a pre-defined ``default`` *context* that comes with a set of *indexes* which are deemed of interest for a general audience. Like for example the ``binaries`` index, which lets you install single-file executables.
