// Boot, sign-in, and the shell both dashboards sit in.
import {
  signIn, signOut, signedIn, rpc, changePassword, sessionUser,
} from './api.js';
import { renderAdmin } from './admin.js';
import { renderStudent } from './student.js';
import { h, clear, card, button, field, input, toast, flashError } from './ui.js';

const root = document.getElementById('app');
let whoami = null;

function loading(text = 'Loading…') {
  clear(root).append(h('div', { class: 'boot' }, h('div', { class: 'spinner' }), h('p', { class: 'muted' }, text)));
}

function fatal(err) {
  clear(root).append(card('Something went wrong',
    h('p', { class: 'muted' }, String(err?.message || err)),
    h('div', { class: 'row end' }, button('Try again', boot, 'btn'))));
}

async function boot() {
  loading('Connecting to the school…');
  if (!signedIn()) return loginScreen();
  try {
    whoami = await rpc('astro_whoami');
  } catch (err) {
    if (err.auth) {
      await signOut();
      return loginScreen('Your session expired. Please sign in again.');
    }
    return fatal(err);
  }
  shell();
}

// --------------------------------------------------------------- sign in ---
function loginScreen(message) {
  const email = input({ type: 'email', autocomplete: 'username', placeholder: 'you@school.com' });
  const password = input({ type: 'password', autocomplete: 'current-password', placeholder: 'Password' });
  const status = h('div', { class: 'muted small' }, message || '');
  const submit = h('button', { class: 'btn primary wide', type: 'submit' }, 'Sign in');

  const form = h('form', {
    class: 'card login',
    onsubmit: async (e) => {
      e.preventDefault();
      status.textContent = 'Signing in…';
      submit.disabled = true;
      try {
        await signIn(email.value, password.value);
        await boot();
      } catch (err) {
        submit.disabled = false;
        const msg = /invalid login credentials/i.test(err.message)
          ? 'Wrong email or password.'
          : /email not confirmed/i.test(err.message)
            ? 'This account has not confirmed its email yet.'
            : err.message;
        status.textContent = msg;
        status.className = 'muted small error-text';
      }
    },
  },
    h('div', { class: 'brand' },
      h('div', { class: 'brand-mark' }, 'A'),
      h('div', {},
        h('h1', {}, 'Astro Smart Attendance'),
        h('p', { class: 'muted small' }, 'Sign in with the account the school gave you'))),
    field('Email', email),
    field('Password', password),
    submit,
    status);

  clear(root).append(h('div', { class: 'login-wrap' }, form,
    h('p', { class: 'muted small center' },
      'Staff: the account your school created. Parents: the email you gave the office.')));
}

// ----------------------------------------------------------------- shell ---
function shell() {
  const user = sessionUser();
  const role = whoami?.role || 'none';
  const school = whoami?.school;

  const header = h('header', { class: 'topbar' },
    h('div', { class: 'brand small' },
      h('div', { class: 'brand-mark' }, 'A'),
      h('div', {},
        h('div', { class: 'school' }, school?.name || 'Astro Smart Attendance'),
        h('div', { class: 'muted small' }, school ? school.code : ''))),
    h('div', { class: 'topbar-right' },
      h('span', { class: `chip ${role === 'admin' ? 'strong' : role === 'student' ? 'leave' : 'muted'}` },
        role === 'student' ? 'Parent' : role === 'none' ? 'No access' : role),
      h('span', { class: 'muted small hide-sm' }, user?.email || ''),
      button('Password', changePasswordFlow, 'btn ghost small'),
      button('Sign out', async () => { await signOut(); whoami = null; boot(); }, 'btn ghost small')));

  const content = h('div', { id: 'view' });
  clear(root).append(header, content);

  if (role === 'admin' || role === 'teacher' || role === 'viewer') {
    renderAdmin(content, { whoami });
  } else if (role === 'student') {
    renderStudent(content, { whoami });
  } else {
    content.append(card('No access yet',
      h('p', {}, 'You are signed in as ', h('b', {}, user?.email || 'this account'),
        ', but the school has not linked this account yet.'),
      h('p', { class: 'muted small' },
        'Ask the office to add you as a staff member, or to link your child to this email address.'),
      h('p', { class: 'muted small' }, `Account id: ${whoami?.user_id || '—'}`),
      h('div', { class: 'row end' },
        button('Sign out', async () => { await signOut(); boot(); }, 'btn ghost'))));
  }
}

async function changePasswordFlow() {
  const next = prompt('New password (at least 6 characters):');
  if (!next) return;
  if (next.length < 6) return toast('Password too short', 'error');
  const again = prompt('Type the new password again:');
  if (again !== next) return toast('The two passwords do not match', 'error');
  try {
    await changePassword(next);
    toast('Password changed');
  } catch (err) {
    flashError(err);
  }
}

window.addEventListener('unhandledrejection', (e) => {
  if (e.reason?.auth) { signOut().then(boot); return; }
  flashError(e.reason);
});

boot();
