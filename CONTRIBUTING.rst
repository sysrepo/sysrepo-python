==============================
Contributing To sysrepo-python
==============================

This is an open source project and all contributions are welcome.

Issues
======

Please create new issues for any bug you discover at
https://github.com/sysrepo/sysrepo-python/issues/new. It is not necessary to
file a bug if you are preparing a patch.

Pull Requests
=============

Here are the steps for submitting a change in the code base:

#. Fork the repository: https://github.com/sysrepo/sysrepo-python/fork

#. Clone your own fork into your development machine::

      git clone https://github.com/<you>/sysrepo-python

#. Create a new branch named after what your are working on::

      git checkout -b my-topic

#. Edit the code and call ``make format`` to ensure your modifications comply
   with the `coding style`__.

   __ https://black.readthedocs.io/en/stable/the_black_code_style.html

   Your contribution must be licensed under the `BSD 3-Clause "New" or "Revised"
   License`__ . At least one copyright notice is expected in new files.

   __ https://spdx.org/licenses/BSD-3-Clause.html

#. If you are adding a new feature or fixing a bug, please consider adding or
   updating unit tests.

#. Before creating commits, run ``make lint`` and ``make tests`` to check if
   your changes do not break anything. You can also run ``make`` which will run
   both.

#. Create commits by following these simple guidelines:

   -  Solve only one problem per commit.
   -  Use a short (less than 72 characters) title on the first line followed by
      an blank line and a more thorough description body.
   -  Wrap the body of the commit message should be wrapped at 72 characters too
      unless it breaks long URLs or code examples.
   -  If the commit fixes a Github issue, include the following line::

        Fixes: #NNNN

   Inspirations:

   https://chris.beams.io/posts/git-commit/
   https://wiki.openstack.org/wiki/GitCommitMessages

#. Push your topic branch in your forked repository::

      git push origin my-topic

   You should get a message from Github explaining how to create a new pull
   request.

#. Wait for a reviewer to merge your work. If minor adjustments are requested,
   use ``git commit --fixup $sha1`` to make it obvious what commit you are
   adjusting. If bigger changes are needed, make them in new separate commits.
   Once the reviewer is happy, please use ``git rebase --autosquash`` to amend
   the commits with their small fixups (if any), and ``git push --force`` on
   your topic branch.

Thank you in advance for your contributions!
