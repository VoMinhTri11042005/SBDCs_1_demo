const fs = require("fs");
const path = require("path");

// Fix Appointments.jsx
const appointmentsPath = path.join(
  __dirname,
  "frontend",
  "src",
  "pages",
  "Appointments.jsx",
);
let appointments = fs.readFileSync(appointmentsPath, "utf-8");

// Add min date to datetime input
appointments = appointments.replace(
  'type="datetime-local" className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 dark:text-slate-50" required value={newApp.appointment_date} onChange={e => setNewApp({...newApp, appointment_date: e.target.value})}',
  'type="datetime-local" min={new Date().toISOString().slice(0, 16)} className="w-full bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl py-3.5 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 dark:text-slate-50" required value={newApp.appointment_date} onChange={e => setNewApp({...newApp, appointment_date: e.target.value})}',
);

fs.writeFileSync(appointmentsPath, appointments);
console.log("✓ Appointments.jsx updated");
