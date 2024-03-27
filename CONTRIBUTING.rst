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

      git checkout -b my-topic -t origin/master

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

#. Once you are happy with your work, you can create a commit (or several
   commits). Follow these general rules:

   -  Address only one issue/topic per commit.
   -  Describe your changes in imperative mood, e.g. *"make xyzzy do frotz"*
      instead of *"[This patch] makes xyzzy do frotz"* or *"[I] changed xyzzy to
      do frotz"*, as if you are giving orders to the codebase to change its
      behaviour.
   -  Limit the first line (title) of the commit message to 60 characters.
   -  Use a short prefix for the commit title for readability with ``git log
      --oneline``. Do not use the `fix:` nor `feature:` prefixes. See recent
      commits for inspiration.
   -  Only use lower case letters for the commit title except when quoting
      symbols or known acronyms.
   -  Use the body of the commit message to actually explain what your patch
      does and why it is useful. Even if your patch is a one line fix, the
      description is not limited in length and may span over multiple
      paragraphs. Use proper English syntax, grammar and punctuation.
   -  If you are fixing an issue, use appropriate ``Closes: <URL>`` or
      ``Fixes: <URL>`` trailers.
   -  If you are fixing a regression introduced by another commit, add a
      ``Fixes: <COMMIT_ID> ("<TITLE>")`` trailer.
   -  When in doubt, follow the format and layout of the recent existing
      commits.
   -  The following trailers are accepted in commits. If you are using multiple
      trailers in a commit, it's preferred to also order them according to this
      list.

      *  ``Closes: <URL>``: close the referenced issue or pull request.
      *  ``Fixes: <SHA> ("<TITLE>")``: reference the commit that introduced
         a regression.
      *  ``Link: <URL>``: any useful link to provide context for your commit.
      *  ``Suggested-by``
      *  ``Requested-by``
      *  ``Reported-by``
      *  ``Co-authored-by``
      *  ``Tested-by``
      *  ``Reviewed-by``
      *  ``Acked-by``
      *  ``Signed-off-by``: Compulsory!

   There is a great reference for commit messages in the `Linux kernel
   documentation`__.

   __ https://www.kernel.org/doc/html/latest/process/submitting-patches.html#describe-your-changes

   IMPORTANT: you must sign-off your work using ``git commit --signoff``. Follow
   the `Linux kernel developer's certificate of origin`__ for more details. All
   contributions are made under the MIT license. If you do not want to disclose
   your real name, you may sign-off using a pseudonym. Here is an example::

       Signed-off-by: Robin Jarry <robin@jarry.cc>

   __ https://www.kernel.org/doc/html/latest/process/submitting-patches.html#sign-your-work-the-developer-s-certificate-of-origin

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
