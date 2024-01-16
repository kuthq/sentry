import {MemberFixture} from 'sentry-fixture/member';
import {UserFixture} from 'sentry-fixture/user';

import type {Member} from 'sentry/types';

export function MembersFixture(params: Member[] = []): Member[] {
  return [
    MemberFixture(),
    {
      id: '2',
      name: 'Sentry 2 Name',
      email: 'sentry2@test.com',
      orgRole: 'member',
      groupOrgRoles: [],
      teamRoles: [],
      dateCreated: '',
      role: 'member',
      roleName: 'Member',
      pending: true,
      flags: {
        'sso:linked': false,
        'sso:invalid': false,
        'idp:provisioned': false,
        'idp:role-restricted': false,
        'member-limit:restricted': false,
        'partnership:restricted': false,
      },
      user: null,
      expired: false,
      inviteStatus: 'approved',
      invite_link: '',
      inviterName: '',
      isOnlyOwner: false,
      orgRoleList: [],
      projects: [],
      roles: [],
      teamRoleList: [],
      teams: [],
    },
    {
      id: '3',
      name: 'Sentry 3 Name',
      email: 'sentry3@test.com',
      orgRole: 'owner',
      groupOrgRoles: [],
      teamRoles: [],
      role: 'owner',
      dateCreated: '',
      expired: false,
      inviteStatus: 'approved',
      invite_link: '',
      inviterName: '',
      roleName: 'Owner',
      isOnlyOwner: false,
      orgRoleList: [],
      projects: [],
      roles: [],
      teamRoleList: [],
      teams: [],
      pending: false,
      flags: {
        'sso:linked': true,
        'sso:invalid': false,
        'idp:provisioned': false,
        'idp:role-restricted': false,
        'member-limit:restricted': false,
        'partnership:restricted': false,
      },
      user: UserFixture(),
    },
    {
      id: '4',
      name: 'Sentry 4 Name',
      email: 'sentry4@test.com',
      orgRole: 'owner',
      groupOrgRoles: [],
      teamRoles: [],
      dateCreated: '',
      role: 'owner',
      roleName: 'Owner',
      pending: false,
      flags: {
        'sso:linked': true,
        'sso:invalid': false,
        'idp:provisioned': false,
        'idp:role-restricted': false,
        'member-limit:restricted': false,
        'partnership:restricted': false,
      },
      user: null,
      expired: false,
      inviteStatus: 'approved',
      invite_link: '',
      inviterName: '',
      isOnlyOwner: false,
      orgRoleList: [],
      projects: [],
      roles: [],
      teamRoleList: [],
      teams: [],
    },
    ...params,
  ];
}
