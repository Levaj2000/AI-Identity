import { useState, useEffect, useRef, useCallback } from 'react'
import type { Organization, OrgMember } from '../types/api'
import {
  getMyOrg,
  createOrg,
  updateOrg,
  deleteOrg,
  listMembers,
  inviteMember,
  updateMemberRole,
  removeMember,
  isApiError,
} from '../services/api'
import { ConfirmModal } from '../components/modals/ConfirmModal'

// ─── Helpers ──────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function TierBadge({ tier }: { tier: string }) {
  const colors: Record<string, string> = {
    free: 'bg-gray-100 text-gray-700 dark:bg-[#1a1a1d] dark:text-[#a1a1aa]',
    starter: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
    pro: 'bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400',
    enterprise: 'bg-[#A6DAFF]/10 text-[#A6DAFF] dark:bg-[#A6DAFF]/10 dark:text-[#A6DAFF]',
  }
  const cls = colors[tier.toLowerCase()] || colors.free
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}
    >
      {tier}
    </span>
  )
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    owner: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
    admin: 'bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400',
    member: 'bg-gray-100 text-gray-700 dark:bg-[#1a1a1d] dark:text-[#a1a1aa]',
  }
  const cls = colors[role] || colors.member
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}
    >
      {role}
    </span>
  )
}

// ─── Toast ────────────────────────────────────────────────────────

function Toast({
  message,
  type,
  onDismiss,
}: {
  message: string
  type: 'success' | 'error'
  onDismiss: () => void
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-fade-in">
      <div
        className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
          type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`}
      >
        {type === 'success' ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
              clipRule="evenodd"
            />
          </svg>
        )}
        {message}
        <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>
    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-[#1a1a1d] dark:bg-[#10131C]">
        <div className="h-6 w-48 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
        <div className="mt-4 h-4 w-64 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
        <div className="mt-6 flex gap-4">
          <div className="h-16 w-32 animate-pulse rounded-lg bg-gray-200 dark:bg-[#1a1a1d]" />
          <div className="h-16 w-32 animate-pulse rounded-lg bg-gray-200 dark:bg-[#1a1a1d]" />
        </div>
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-[#1a1a1d] dark:bg-[#10131C]">
        <div className="h-6 w-36 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-gray-200 dark:bg-[#1a1a1d]" />
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Create Org Card ──────────────────────────────────────────────

function CreateOrgCard({ onCreated }: { onCreated: (org: Organization) => void }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const org = await createOrg(name.trim())
      onCreated(org)
    } catch (err) {
      setError(isApiError(err) ? err.message : 'Failed to create organization')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center dark:border-[#1a1a1d] dark:bg-[#10131C]">
        {/* Icon */}
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#A6DAFF]/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-7 w-7 text-[#A6DAFF]"
          >
            <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
          </svg>
        </div>

        <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">
          Create Your Organization
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-[#a1a1aa]">
          Bring your team together. Create an organization to share agents and manage access.
        </p>

        <form onSubmit={handleCreate} className="mt-6 space-y-4">
          <input
            type="text"
            placeholder="Organization name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#2a2a2d] dark:bg-[#04070D] dark:text-[#e4e4e7] dark:placeholder-[#52525b]"
            required
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="w-full rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Organization'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ─── Inline Editable Name ─────────────────────────────────────────

function InlineEditName({
  value,
  onSave,
}: {
  value: string
  onSave: (name: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  async function save() {
    const trimmed = draft.trim()
    if (!trimmed || trimmed === value) {
      setDraft(value)
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onSave(trimmed)
      setEditing(false)
    } catch {
      setDraft(value)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') save()
    if (e.key === 'Escape') {
      setDraft(value)
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={handleKeyDown}
        disabled={saving}
        className="rounded-lg border border-[#A6DAFF] bg-white px-3 py-1.5 text-xl font-bold text-gray-900 focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:bg-[#04070D] dark:text-[#e4e4e7]"
      />
    )
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="group flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-[#e4e4e7]"
      title="Click to edit"
    >
      {value}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="h-4 w-4 text-gray-400 opacity-0 transition-opacity group-hover:opacity-100"
      >
        <path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z" />
      </svg>
    </button>
  )
}

// ─── Main Page ────────────────────────────────────────────────────

export function OrganizationPage() {
  const [org, setOrg] = useState<Organization | null>(null)
  const [members, setMembers] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(true)
  const [noOrg, setNoOrg] = useState(false)

  // Invite form
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)

  // Modals
  const [deleteModal, setDeleteModal] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [removeMemberModal, setRemoveMemberModal] = useState<OrgMember | null>(null)
  const [removeMemberLoading, setRemoveMemberLoading] = useState(false)

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }, [])

  // ─── Data Loading ───────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true)
    setNoOrg(false)
    try {
      const orgData = await getMyOrg()
      setOrg(orgData)
      const membersData = await listMembers()
      setMembers(membersData)
    } catch (err) {
      if (isApiError(err) && err.status === 404) {
        setNoOrg(true)
      } else {
        showToast(isApiError(err) ? err.message : 'Failed to load organization', 'error')
      }
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => {
    loadData()
  }, [loadData])

  // ─── Actions ────────────────────────────────────────────────────

  async function handleUpdateName(name: string) {
    const updated = await updateOrg(name)
    setOrg(updated)
    showToast('Organization name updated', 'success')
  }

  async function handleDeleteOrg() {
    setDeleteLoading(true)
    try {
      await deleteOrg()
      setOrg(null)
      setMembers([])
      setNoOrg(true)
      setDeleteModal(false)
      showToast('Organization deleted', 'success')
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to delete organization', 'error')
    } finally {
      setDeleteLoading(false)
    }
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail.trim()) return
    setInviteLoading(true)
    setInviteError(null)
    try {
      const member = await inviteMember(inviteEmail.trim(), inviteRole)
      setMembers((prev) => [...prev, member])
      setInviteEmail('')
      setInviteRole('member')
      setShowInvite(false)
      showToast(`Invited ${member.email}`, 'success')
      // Refresh org to get updated member_count
      try {
        const updated = await getMyOrg()
        setOrg(updated)
      } catch {
        // non-critical
      }
    } catch (err) {
      setInviteError(isApiError(err) ? err.message : 'Failed to invite member')
    } finally {
      setInviteLoading(false)
    }
  }

  async function handleChangeRole(userId: string, role: string) {
    try {
      const updated = await updateMemberRole(userId, role)
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? updated : m)))
      showToast('Role updated', 'success')
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to update role', 'error')
    }
  }

  async function handleRemoveMember() {
    if (!removeMemberModal) return
    setRemoveMemberLoading(true)
    try {
      await removeMember(removeMemberModal.user_id)
      setMembers((prev) => prev.filter((m) => m.user_id !== removeMemberModal.user_id))
      setRemoveMemberModal(null)
      showToast('Member removed', 'success')
      // Refresh org to get updated member_count
      try {
        const updated = await getMyOrg()
        setOrg(updated)
      } catch {
        // non-critical
      }
    } catch (err) {
      showToast(isApiError(err) ? err.message : 'Failed to remove member', 'error')
    } finally {
      setRemoveMemberLoading(false)
    }
  }

  // ─── Render ─────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">Organization</h1>
        <Skeleton />
      </div>
    )
  }

  if (noOrg) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">Organization</h1>
        <CreateOrgCard
          onCreated={(newOrg) => {
            setOrg(newOrg)
            setNoOrg(false)
            showToast('Organization created!', 'success')
            loadData()
          }}
        />
        {toast && (
          <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">Organization</h1>

      {/* ── Section 1: Org Info ─────────────────────────────────────── */}
      {org && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-[#1a1a1d] dark:bg-[#10131C]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <InlineEditName value={org.name} onSave={handleUpdateName} />
              <div className="flex items-center gap-3">
                <TierBadge tier={org.tier} />
                <span className="text-xs text-gray-500 dark:text-[#52525b]">
                  Created {formatDate(org.created_at)}
                </span>
              </div>
            </div>
            <button
              onClick={() => setDeleteModal(true)}
              className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
            >
              Delete Organization
            </button>
          </div>

          {/* Stats */}
          <div className="mt-6 flex flex-wrap gap-4">
            <div className="rounded-lg border border-gray-200 px-4 py-3 dark:border-[#1a1a1d]">
              <p className="text-xs text-gray-500 dark:text-[#52525b]">Members</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">
                {org.member_count}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 px-4 py-3 dark:border-[#1a1a1d]">
              <p className="text-xs text-gray-500 dark:text-[#52525b]">Agents</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-[#e4e4e7]">
                {org.agent_count}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 2: Team Members ────────────────────────────────── */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-[#1a1a1d] dark:bg-[#10131C]">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-[#e4e4e7]">Team Members</h2>
          <button
            onClick={() => setShowInvite(!showInvite)}
            className="rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80"
          >
            {showInvite ? 'Cancel' : 'Invite Member'}
          </button>
        </div>

        {/* Invite Form */}
        {showInvite && (
          <form
            onSubmit={handleInvite}
            className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-[#1a1a1d] dark:bg-[#04070D]"
          >
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-[#a1a1aa]">
                Email
              </label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#2a2a2d] dark:bg-[#04070D] dark:text-[#e4e4e7] dark:placeholder-[#52525b]"
                required
              />
            </div>
            <div className="w-32">
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-[#a1a1aa]">
                Role
              </label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#2a2a2d] dark:bg-[#04070D] dark:text-[#e4e4e7]"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={inviteLoading || !inviteEmail.trim()}
              className="rounded-lg bg-[#A6DAFF] px-4 py-2 text-sm font-semibold text-[#04070D] transition-colors hover:bg-[#A6DAFF]/80 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {inviteLoading ? 'Sending...' : 'Send Invite'}
            </button>
            {inviteError && <p className="w-full text-sm text-red-500">{inviteError}</p>}
          </form>
        )}

        {/* Members Table */}
        {members.length === 0 ? (
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500 dark:text-[#52525b]">
              No team members yet. Invite someone to get started.
            </p>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-[#1a1a1d]">
                  <th className="pb-3 pr-4 font-medium text-gray-500 dark:text-[#52525b]">Email</th>
                  <th className="pb-3 pr-4 font-medium text-gray-500 dark:text-[#52525b]">Role</th>
                  <th className="pb-3 pr-4 font-medium text-gray-500 dark:text-[#52525b]">
                    Joined
                  </th>
                  <th className="pb-3 font-medium text-gray-500 dark:text-[#52525b]">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-[#1a1a1d]">
                {members.map((member) => (
                  <tr key={member.user_id}>
                    <td className="py-3 pr-4 text-gray-900 dark:text-[#e4e4e7]">{member.email}</td>
                    <td className="py-3 pr-4">
                      {member.role === 'owner' ? (
                        <RoleBadge role={member.role} />
                      ) : (
                        <select
                          value={member.role}
                          onChange={(e) => handleChangeRole(member.user_id, e.target.value)}
                          className="rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-900 focus:border-[#A6DAFF] focus:outline-none focus:ring-1 focus:ring-[#A6DAFF] dark:border-[#2a2a2d] dark:bg-[#04070D] dark:text-[#e4e4e7]"
                        >
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                        </select>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-gray-600 dark:text-[#a1a1aa]">
                      {formatDate(member.joined_at)}
                    </td>
                    <td className="py-3">
                      {member.role === 'owner' ? (
                        <span className="text-xs text-gray-400 dark:text-[#52525b]">--</span>
                      ) : (
                        <button
                          onClick={() => setRemoveMemberModal(member)}
                          className="rounded-lg px-3 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Modals ─────────────────────────────────────────────────── */}
      {deleteModal && (
        <ConfirmModal
          title="Delete Organization"
          message="This will permanently delete your organization, remove all members, and unassign all agents. This action cannot be undone."
          confirmLabel="Delete Organization"
          confirmVariant="danger"
          isLoading={deleteLoading}
          onConfirm={handleDeleteOrg}
          onCancel={() => setDeleteModal(false)}
        />
      )}

      {removeMemberModal && (
        <ConfirmModal
          title="Remove Member"
          message={`Remove ${removeMemberModal.email} from the organization? They will lose access to all shared agents.`}
          confirmLabel="Remove"
          confirmVariant="danger"
          isLoading={removeMemberLoading}
          onConfirm={handleRemoveMember}
          onCancel={() => setRemoveMemberModal(null)}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </div>
  )
}
