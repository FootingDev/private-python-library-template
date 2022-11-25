Public Python Package Template
##############################

This repository provides a template for a pip-installable private Python package
deployed using Footing's cloud.

This is a `cookiecutter <https://cookiecutter.readthedocs.io/en/latest/>`__
template that can be used by
`footing <https://github.com/Opus10/footing/>`__ to create and manage the
project.

A new private python package can be started with::

    pip3 install footing
    footing setup git@github.com:FootingDev/private-python-library-template.git

**Note** when calling ``footing setup``, a project will be created locally and
it will also be set up on Github.
Do **not** create anything on Github before using this template.

This template assumes the user has a ``GITHUB_API_TOKEN`` environment variable
that contains a Github personal access token. Create one by going to
"https://github.com/settings/tokens" and clicking "Generate New Token".
Select the top-level "repo" checkbox as the only scope.

The following docs cover the parameters needed for the template and more
information on how this template is used in practice.

Template Parameters
===================

When calling ``footing setup``, the user will be prompted for template
parameters. These parameters are defined in the cookiecutter.json file and are
as follows:

1. ``org_name``: The Github org or user name.
2. ``repo_name``: The name of the repository **and** and name of the python
   package. Be sure that the name isn't taken before creation.
3. ``module_name``: The name of the Python module that will be imported as a
   library. Modules must have underscores
   (i.e. ``import my_installable_package``)
4. ``short_description``: A short description of the project. This will be
   added as the Github repo description.
