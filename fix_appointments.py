#!/usr/bin/env python3
import re

# Fix Appointments.jsx - add min date
with open('frontend/src/pages/Appointments.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add min attribute to datetime-local input
content = content.replace(
    'type="datetime-local" className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 dark:text-slate-50" required value={newApp.appointment_date} onChange={e => setNewApp({...newApp, appointment_date: e.target.value})}',
    'type="datetime-local" min={new Date().toISOString().slice(0, 16)} className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 dark:text-slate-50" required value={newApp.appointment_date} onChange={e => setNewApp({...newApp, appointment_date: e.target.value})}'
)

with open('frontend/src/pages/Appointments.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('✓ Appointments.jsx updated with min date')
