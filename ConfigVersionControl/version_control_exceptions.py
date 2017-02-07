# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php


class VersionControlException(Exception):
    def __init__(self, err):
        self.message = str(err)

    def __str__(self):
        return self.message


class AddToVersionControlException(VersionControlException):
    def __init__(self, err):
        super(AddToVersionControlException, self).__init__(err)


class UnlockVersionControlException(VersionControlException):
    def __init__(self, err):
        super(UnlockVersionControlException, self).__init__(err)


class CommitToVersionControlException(VersionControlException):
    def __init__(self, err):
        super(CommitToVersionControlException, self).__init__(err)


class RemoveFromVersionControlException(VersionControlException):
    def __init__(self, err):
        super(RemoveFromVersionControlException, self).__init__(err)


class UpdateFromVersionControlException(VersionControlException):
    def __init__(self, err):
        super(UpdateFromVersionControlException, self).__init__(err)


class NotUnderVersionControl(VersionControlException):
    def __init__(self, err):
        super(NotUnderVersionControl, self).__init__(err)


class PullFromVersionControlException(VersionControlException):
    def __init__(self, err):
        super(PullFromVersionControlException, self).__init__(err)


class NotUnderAllowedBranchException(VersionControlException):
    def __init__(self, err):
        super(NotUnderAllowedBranchException, self).__init__(err)


class PushToVersionControlException(VersionControlException):
    def __init__(self, err):
        super(PushToVersionControlException, self).__init__(err)


