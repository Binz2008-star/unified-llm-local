// update.js
const fs = require('fs');
const si = require('systeminformation');
const os = require('os');

(async () => {
  // --- CPU ---
  const cpuInfo = await si.cpu();
  const currentLoad = await si.currentLoad(); // overall & per‑core loads

  // per‑core CPU percentages (0‑100).  currentLoad.cpus is an array of objects.
  const perCore = (currentLoad.cpus || []).map(c => c.load ?? 0); // array of loads (0‑100)

  // overall CPU % – simple average of all cores
  const overallCpu = perCore.length
    ? perCore.reduce((a, b) => a + b, 0) / perCore.length
    : 0;

  // per‑core CPU percentages (same length as cores)
  const cpuCores = perCore.map(load => Math.round(load));

  // CPU frequency – systeminformation does not expose MHz on Windows,
  // fall back to os.cpus() (may be undefined)
  const cpuFreq = os.cpus().map(c => c.mhz ?? null);

  // --- Memory ---
  const memInfo = await si.mem();
  // memInfo has used, total, free, active (all in bytes)
  const memUsed = memInfo.used / 1024 / 1024 / 1024; // GB
  const memTotal = memInfo.total / 1024 / 1024 / 1024; // GB
  const memFree = memInfo.free / 1024 / 1024 / 1024; // GB
  const memActive = memInfo.active != null ? memInfo.active / 1024 / 1024 / 1024 : null; // GB

  // --- Disk ---
  const diskInfo = await si.fsSize(); // array of {fs, size, used, available, use%}
  const primaryDisk = diskInfo.find(d => d.fs === 'C:') || diskInfo[0] || {};
  const diskUsed = (primaryDisk.used / 1024 / 1024 / 1024).toFixed(2);
  const diskTotal = (primaryDisk.size / 1024 / 1024 / 1024).toFixed(2);
  const diskFree = (primaryDisk.available / 1024 / 1024 / 1024).toFixed(2);
  const diskUsePct = primaryDisk.use != null ? primaryDisk.use : Math.round((primaryDisk.used / primaryDisk.size) * 100);

  // --- Network ---
  const netInfo = await si.networkStats();
  const primaryIf = netInfo.find(n => n.iface !== 'Loopback' && n.rx_bytes > 0) || netInfo[0] || {};
  const netIn = primaryIf.rx_bytes ?? 0; // bytes since boot
  const netOut = primaryIf.tx_bytes ?? 0;

  // --- Processes ---
  // systeminformation does not give a full process list, we pull a minimal set via os.node()
  // For a lightweight approach we just report the total process count.
  const procCount = await si.currentLoad(); // currentLoad.currentprocs
  // Build a very small process list from the OS (name, pid, cpu% approximate)
  const {execSync} = require('child_process');
  let processList = [];
  try {
    // Windows tasklist parsing – keep it simple
    const tl = execSync('tasklist /FO CSV /NH').toString();
    const rows = tl.split('\n').map(r => r.split('","')).filter(r => r.length >= 3);
    processList = rows.slice(0, 20).map(r => ({
      name: r[0].replace(/"/g, '').replace(/.exe$/i, '') || 'unknown',
      pid: parseInt(r[1], 10) || null,
      // cpu% not easily CSV; we set 0
      cpu: 0,
      memory: null // will be filled later if needed
    }));
  } catch (e) {
    // ignore errors – processList stays empty
  }

  // --- Battery ---
  const batteryInfo = await si.battery();
  const batteryPercent = batteryInfo.hasBattery ? Math.round(batteryInfo.percent) : null;
  const batteryCharging = batteryInfo.acConnected ?? false;

  // --- Temperature ---
  const tempInfo = await si.cpuTemperature();
  const temperature = tempInfo.main ? tempInfo.main.temp : null; // Celsius, may be null

  // --- System identification ---
  const hostName = os.hostname();
  const osType = `${os.type()} ${os.release()}`;

  // --- Assemble the data object expected by both dashboards ---
  const data = {
    // ---- NOVA core fields ----
    cpu: Number(overallCpu.toFixed(1)),           // % overall
    mem: {
      used: Number(memUsed.toFixed(2)),
      total: Number(memTotal.toFixed(2)),
      free: Number(memFree.toFixed(2)),
      active: Number(memActive?.toFixed(2) ?? 0)
    },
    disk: {
      used: Number(diskUsed),
      total: Number(diskTotal),
      free: Number(diskFree),
      usePct: Number(diskUsePct)
    },
    net: {
      in: netIn,
      out: netOut
    },
    procs: procCount.currentprocs,
    battery: batteryPercent != null ? batteryPercent : null,
    temperature: temperature != null ? Number(temperature.toFixed(1)) : null,

    // ---- JARVIS‑specific extra fields ----
    cpu_cores: cpuCores,                     // array of per‑core % (length = core count)
    cpu_freq: cpuFreq,                       // array of MHz (may contain nulls)
    processes: processList,                  // limited list [{name, pid, cpu, memory}]
    system: {
      host: hostName,
      os: osType,
      gpu: null                               // GPU info not gathered here
    }
  };

  fs.writeFileSync('data.json', JSON.stringify(data, null, 2));
  console.log('✅ data.json updated with full metric set');
})();