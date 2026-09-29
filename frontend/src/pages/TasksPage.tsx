import React, { useState } from 'react';
import { Plus, Pencil, Trash2, CheckSquare } from 'lucide-react';
import { useTasks } from '../hooks/useTasks';
import type { Task, Priority, TaskCategory } from '../types';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Checkbox } from '../components/ui/Checkbox';
import { Modal } from '../components/ui/Modal';
import { Tabs } from '../components/ui/Tabs';
import { EmptyState } from '../components/ui/EmptyState';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { RowActions } from '../components/ui/RowActions';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { Toolbar, SearchField, FilterSelect, TableFooter } from '../components/ui/Toolbar';
import { DesktopOnly, MobileList, MobileRow } from '../components/ui/ResponsiveList';
import { formatDayLabel, formatTime, daysUntil, todayISO } from '../utils/formatters';
import { PRIORITY_STYLES, CATEGORY_LABELS, statusStyle } from '../utils/status';
import { cn } from '../utils/cn';

type StatusFilter = 'open' | 'duesoon' | 'high' | 'completed' | 'all';

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

export const TasksPage: React.FC = () => {
  const { tasks, createTask, isCreating, updateTask, toggleComplete, deleteTask } = useTasks();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('open');
  const [categoryFilter, setCategoryFilter] = useState<TaskCategory | 'all'>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTaskId, setDeletingTaskId] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<TaskCategory>('academic');
  const [subject, setSubject] = useState('');
  const [priority, setPriority] = useState<Priority>('medium');
  const [dueDate, setDueDate] = useState(todayISO());
  const [dueTime, setDueTime] = useState('23:59');

  const openCreateModal = () => {
    setEditingTask(null);
    setTitle('');
    setDescription('');
    setCategory('academic');
    setSubject('');
    setPriority('medium');
    setDueDate(todayISO());
    setDueTime('23:59');
    setIsModalOpen(true);
  };

  const openEditModal = (task: Task) => {
    setEditingTask(task);
    setTitle(task.title);
    setDescription(task.description || '');
    setCategory(task.category);
    setSubject(task.subject || '');
    setPriority(task.priority);
    setDueDate(task.dueDate);
    setDueTime(task.dueTime || '23:59');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const payload = { title, description, category, subject, priority, dueDate, dueTime };
    if (editingTask) {
      await updateTask({ id: editingTask.id, updates: payload });
    } else {
      await createTask({ ...payload, status: 'pending' });
    }
    setIsModalOpen(false);
  };

  const isOpen = (t: Task) => t.status !== 'completed';
  const counts = {
    open: tasks.filter(isOpen).length,
    duesoon: tasks.filter((t) => isOpen(t) && daysUntil(t.dueDate) <= 2).length,
    high: tasks.filter((t) => isOpen(t) && t.priority === 'high').length,
    completed: tasks.filter((t) => !isOpen(t)).length,
    all: tasks.length,
  };

  const query = search.trim().toLowerCase();
  const filteredTasks = tasks
    .filter((t) => {
      if (query && !`${t.title} ${t.subject ?? ''} ${t.description ?? ''}`.toLowerCase().includes(query)) return false;
      if (categoryFilter !== 'all' && t.category !== categoryFilter) return false;
      switch (statusFilter) {
        case 'open':
          return isOpen(t);
        case 'duesoon':
          return isOpen(t) && daysUntil(t.dueDate) <= 2;
        case 'high':
          return isOpen(t) && t.priority === 'high';
        case 'completed':
          return !isOpen(t);
        default:
          return true;
      }
    })
    .sort((a, b) => Number(!isOpen(a)) - Number(!isOpen(b)) || a.dueDate.localeCompare(b.dueDate));

  return (
    <Page>
      <PageHeader
        title="Tasks"
        description="Assignments and to-dos across academics, career, finances and personal life."
        actions={
          <Button onClick={openCreateModal} leftIcon={<Plus className="size-4" />}>
            New task
          </Button>
        }
      />

      <Toolbar>
        <Tabs
          variant="pills"
          activeTab={statusFilter}
          onChange={(id) => setStatusFilter(id as StatusFilter)}
          tabs={[
            { id: 'open', label: 'Open', badge: counts.open },
            { id: 'duesoon', label: 'Due soon', badge: counts.duesoon },
            { id: 'high', label: 'High priority', badge: counts.high },
            { id: 'completed', label: 'Done', badge: counts.completed },
            { id: 'all', label: 'All', badge: counts.all },
          ]}
        />
        <div className="flex items-center gap-2">
          <SearchField value={search} onChange={setSearch} placeholder="Search tasks" />
          <FilterSelect
            label="Category"
            value={categoryFilter}
            onChange={(v) => setCategoryFilter(v as TaskCategory | 'all')}
            options={[{ value: 'all', label: 'All categories' }, ...CATEGORY_OPTIONS]}
          />
        </div>
      </Toolbar>

      <Card flush className="overflow-hidden">
        {filteredTasks.length === 0 ? (
          <EmptyState
            bare
            icon={<CheckSquare />}
            title={query || categoryFilter !== 'all' ? 'No matching tasks' : 'No tasks here'}
            description={
              query || categoryFilter !== 'all'
                ? 'Try a different search or filter.'
                : 'Create a task, or ask the assistant to add one for you.'
            }
            actionLabel="New task"
            onAction={openCreateModal}
          />
        ) : (
          <>
            <MobileList>
              {filteredTasks.map((t) => {
                const done = !isOpen(t);
                const p = statusStyle(PRIORITY_STYLES, t.priority);
                const overdue = !done && daysUntil(t.dueDate) < 0;
                return (
                  <MobileRow
                    key={t.id}
                    onClick={() => openEditModal(t)}
                    muted={done}
                    leading={
                      <Checkbox
                        checked={done}
                        onChange={() => toggleComplete(t.id)}
                        aria-label={done ? `Reopen "${t.title}"` : `Complete "${t.title}"`}
                      />
                    }
                    title={t.title}
                    subtitle={t.subject || CATEGORY_LABELS[t.category]}
                    meta={
                      <>
                        <Badge variant={p.variant} dot>
                          {p.label}
                        </Badge>
                        <span className={cn('text-xs tabular', overdue ? 'text-danger font-medium' : 'text-fg-subtle')}>
                          {overdue ? 'Overdue · ' : 'Due '}
                          {formatDayLabel(t.dueDate)}
                          {t.dueTime ? `, ${formatTime(t.dueTime)}` : ''}
                        </span>
                      </>
                    }
                    actions={
                      <RowActions
                        label={`Actions for ${t.title}`}
                        items={[
                          { id: 'edit', label: 'Edit', icon: <Pencil />, onClick: () => openEditModal(t) },
                          { id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, separated: true, onClick: () => setDeletingTaskId(t.id) },
                        ]}
                      />
                    }
                  />
                );
              })}
            </MobileList>
            <DesktopOnly>
            <Table>
              <THead>
                <tr>
                  <TH className="w-10 pr-0">
                    <span className="sr-only">Done</span>
                  </TH>
                  <TH>Task</TH>
                  <TH className="hidden md:table-cell">Category</TH>
                  <TH className="hidden sm:table-cell">Priority</TH>
                  <TH>Due</TH>
                  <TH className="w-12">
                    <span className="sr-only">Actions</span>
                  </TH>
                </tr>
              </THead>
              <TBody>
                {filteredTasks.map((t) => {
                  const done = !isOpen(t);
                  const p = statusStyle(PRIORITY_STYLES, t.priority);
                  const days = daysUntil(t.dueDate);
                  const overdue = !done && days < 0;
                  return (
                    <TR key={t.id} interactive onClick={() => openEditModal(t)}>
                      <TD className="pr-0">
                        <Checkbox
                          checked={done}
                          onChange={() => toggleComplete(t.id)}
                          aria-label={done ? `Reopen "${t.title}"` : `Complete "${t.title}"`}
                        />
                      </TD>
                      <TD className="w-full max-w-0">
                        <p className={cn('font-medium truncate', done ? 'text-fg-subtle line-through' : 'text-fg')}>{t.title}</p>
                        {(t.subject || t.description) && (
                          <p className="text-xs text-fg-subtle truncate mt-0.5">{t.subject || t.description}</p>
                        )}
                      </TD>
                      <TD className="hidden md:table-cell text-fg-muted">{CATEGORY_LABELS[t.category]}</TD>
                      <TD className="hidden sm:table-cell">
                        <Badge variant={p.variant} dot>
                          {p.label}
                        </Badge>
                      </TD>
                      <TD className="whitespace-nowrap">
                        <span className={cn('tabular', overdue ? 'text-danger font-medium' : 'text-fg-muted')}>
                          {overdue ? `Overdue · ${formatDayLabel(t.dueDate)}` : formatDayLabel(t.dueDate)}
                        </span>
                        {t.dueTime && <span className="block text-xs text-fg-faint">{formatTime(t.dueTime)}</span>}
                      </TD>
                      <TD>
                        <RowActions
                          label={`Actions for ${t.title}`}
                          items={[
                            { id: 'edit', label: 'Edit', icon: <Pencil />, onClick: () => openEditModal(t) },
                            {
                              id: 'delete',
                              label: 'Delete',
                              icon: <Trash2 />,
                              destructive: true,
                              separated: true,
                              onClick: () => setDeletingTaskId(t.id),
                            },
                          ]}
                        />
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
            </DesktopOnly>
            <TableFooter shown={filteredTasks.length} total={tasks.length} noun="tasks" />
          </>
        )}
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTask ? 'Edit task' : 'New task'}
        description={editingTask ? undefined : 'Tasks can also be created by approving an assistant proposal.'}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="task-form" isLoading={isCreating}>
              {editingTask ? 'Save changes' : 'Create task'}
            </Button>
          </>
        }
      >
        <form id="task-form" onSubmit={handleFormSubmit} className="space-y-4">
          <Input
            label="Title"
            placeholder="e.g. ML problem set 4"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            autoFocus
          />
          <Textarea
            label="Description"
            placeholder="Optional details"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value as TaskCategory)}
              options={CATEGORY_OPTIONS}
            />
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as Priority)}
              options={[
                { value: 'high', label: 'High' },
                { value: 'medium', label: 'Medium' },
                { value: 'low', label: 'Low' },
              ]}
            />
          </div>
          {category === 'academic' && (
            <Input
              label="Subject"
              placeholder="e.g. Machine Learning"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          )}
          <div className="grid grid-cols-2 gap-4">
            <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
            <Input label="Due time" type="time" value={dueTime} onChange={(e) => setDueTime(e.target.value)} />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deletingTaskId}
        onClose={() => setDeletingTaskId(null)}
        onConfirm={async () => {
          if (deletingTaskId) {
            await deleteTask(deletingTaskId);
            setDeletingTaskId(null);
          }
        }}
        title="Delete task?"
        message="This task will be permanently removed. This can't be undone."
      />
    </Page>
  );
};
