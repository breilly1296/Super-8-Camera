const INTERFACE_SPECS = [
  {
    category: 'Dovetail',
    specs: [
      { label: 'Angle', value: '60 deg' },
      { label: 'Top Width', value: '4 mm' },
      { label: 'Base Width', value: '6 mm' },
      { label: 'Depth', value: '3 mm' },
    ],
  },
  {
    category: 'Thumb Screws',
    specs: [
      { label: 'Thread', value: 'M3' },
      { label: 'Spacing', value: '20 mm' },
    ],
  },
  {
    category: 'Connectors (J1-J7)',
    specs: [
      { label: 'J1 — Motor', value: 'VH 2-pin' },
      { label: 'J2 — Encoder', value: 'XH 4-pin' },
      { label: 'J3 — Shutter Sensor', value: 'XH 3-pin' },
      { label: 'J4 — Trigger', value: 'XH 2-pin' },
      { label: 'J5 — Film Door Switch', value: 'XH 2-pin' },
      { label: 'J6 — Battery', value: 'VH 2-pin' },
      { label: 'J7 — Expansion (MOD-EXP)', value: 'XH 10-pin' },
    ],
  },
  {
    category: 'Fasteners (allowed only)',
    specs: [
      { label: 'Metric', value: 'M2, M2.5, M3' },
      { label: 'Imperial', value: '1/4"-20 (tripod mount)' },
    ],
  },
];

const EXPANSION_SIGNALS = [
  { pin: 1, signal: 'SDA', description: 'I2C data' },
  { pin: 2, signal: 'SCL', description: 'I2C clock' },
  { pin: 3, signal: 'TX', description: 'UART transmit' },
  { pin: 4, signal: 'RX', description: 'UART receive' },
  { pin: 5, signal: 'PWM1', description: 'PWM channel 1' },
  { pin: 6, signal: 'PWM2', description: 'PWM channel 2' },
  { pin: 7, signal: '3V3', description: '3.3 V power rail' },
  { pin: 8, signal: '5V', description: '5.0 V power rail' },
  { pin: 9, signal: 'GND', description: 'Ground' },
  { pin: 10, signal: 'GND', description: 'Ground' },
];

const COMMUNITY_MODULES = [
  { name: 'Intervalometer', description: 'Time-lapse control with programmable intervals, ramp, and bulb exposure.' },
  { name: 'Light Meter', description: 'Ambient light sensor with exposure readout on a small OLED.' },
  { name: 'Bluetooth Remote', description: 'Wireless trigger and frame counter via BLE.' },
  { name: 'GPS Logger', description: 'Geotag each cartridge with start/stop coordinates.' },
  { name: 'Audio Sync', description: 'Timecode blink or pilot tone generator for double-system sound.' },
  { name: 'Frame Counter Display', description: 'Remaining footage readout for Super 8 cartridges.' },
];

const COMPARISON = [
  {
    feature: 'Price',
    super8: '$249 kit / $599 assembled',
    kodak: '~$5,500',
    vintage: '$200-800',
  },
  {
    feature: 'Repairability',
    super8: 'Full — every part replaceable',
    kodak: 'Limited — sealed modules',
    vintage: 'Depends on parts supply',
  },
  {
    feature: 'Parts Availability',
    super8: 'Open files, buy individually',
    kodak: 'Manufacturer only',
    vintage: 'Scavenged / NOS only',
  },
  {
    feature: 'Lens Mount',
    super8: 'C-mount (universal)',
    kodak: 'Proprietary fixed zoom',
    vintage: 'Varies (often proprietary)',
  },
  {
    feature: 'Open Source',
    super8: 'Yes (CERN-OHL-S v2)',
    kodak: 'No',
    vintage: 'No',
  },
  {
    feature: 'Modular Design',
    super8: 'Yes — 7 swappable modules',
    kodak: 'No',
    vintage: 'No',
  },
  {
    feature: 'Frame Rate',
    super8: '18 / 24 fps (firmware selectable)',
    kodak: '9 / 12 / 18 / 24 / 25 fps',
    vintage: 'Typically 18 fps only',
  },
  {
    feature: 'Weight',
    super8: '~691 g',
    kodak: '~800 g (est.)',
    vintage: '~500-900 g',
  },
];

export default function About() {
  return (
    <div className="space-y-14">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-100">About</h1>
        <p className="text-zinc-400 mt-1">
          Philosophy, interface standard, expansion system, and licensing.
        </p>
      </div>

      {/* Framework for Film */}
      <section>
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">
          Framework for Film
        </h2>
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6 space-y-4">
          <p className="text-zinc-300 leading-relaxed">
            This project exists because cameras should be repairable, modular, and transparent
            -- the same principles that{' '}
            <a
              href="https://frame.work"
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-400 hover:text-amber-300 underline underline-offset-2 transition-colors"
            >
              Framework laptops
            </a>{' '}
            brought to personal computing. When a claw tip wears down after 100,000 frames,
            you should be able to buy a $5 replacement and swap it in two minutes -- not send the
            entire camera to a factory or throw it away.
          </p>
          <p className="text-zinc-300 leading-relaxed">
            Every module slides in on a dovetail rail and locks with two M3 thumb screws. Every
            connector is keyed JST so it can only go in one way. Every precision part is sold
            individually with full engineering drawings published under an open hardware license.
            If we stop making parts, anyone with a CNC mill or 3D printer can make their own.
          </p>
          <p className="text-zinc-300 leading-relaxed">
            The camera is designed around a{' '}
            <span className="text-amber-400 font-semibold">frozen interface standard (v1.0)</span>{' '}
            that guarantees forward compatibility. As long as a module conforms to v1.0 dimensions
            and pinouts, it will fit any v1.0 camera body -- whether made by us, by you, or by a
            community contributor ten years from now.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            {[
              { title: 'Modular', desc: '7 hot-swappable modules on dovetail rails. No glue, no soldering.' },
              { title: 'Repairable', desc: 'Every wear part sold individually. Longest swap: 5 minutes with a screwdriver.' },
              { title: 'Open Source', desc: 'CAD, firmware, BOM, and docs published under CERN-OHL-S v2.' },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-zinc-900/60 border border-zinc-700/50 rounded-lg p-4"
              >
                <h4 className="text-amber-500 font-semibold text-sm mb-1">
                  {item.title}
                </h4>
                <p className="text-zinc-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Interface Standard v1.0 */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-2xl font-bold text-zinc-100">
            Interface Standard v1.0
          </h2>
          <span className="px-2.5 py-0.5 bg-amber-600/15 text-amber-500 text-xs font-mono font-bold rounded border border-amber-600/30">
            FROZEN
          </span>
        </div>
        <p className="text-zinc-400 text-sm mb-4">
          These mechanical and electrical interfaces are permanently locked. Any future module
          claiming v1.0 compatibility must conform to these exact dimensions and pinouts.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {INTERFACE_SPECS.map((group) => (
            <div
              key={group.category}
              className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden"
            >
              <h3 className="text-sm font-semibold text-zinc-100 px-5 py-2.5 border-b border-zinc-700 bg-zinc-800/80 uppercase tracking-wider">
                {group.category}
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {group.specs.map((spec, i) => (
                    <tr
                      key={spec.label}
                      className={i % 2 === 0 ? 'bg-zinc-900/40' : 'bg-zinc-900/20'}
                    >
                      <td className="px-5 py-2 text-zinc-400 font-medium">
                        {spec.label}
                      </td>
                      <td className="px-5 py-2 text-zinc-100 font-mono text-xs">
                        {spec.value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>

      {/* Expansion Slot */}
      <section>
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">
          Expansion Slot (MOD-EXP)
        </h2>
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6 space-y-5">
          <p className="text-zinc-300 text-sm leading-relaxed">
            The camera includes a 10-pin JST-XH expansion connector (J7) that exposes I2C, UART,
            two PWM channels, and both power rails. Community-designed modules slide into the
            expansion bay and connect with a single cable.
          </p>

          {/* Pinout table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-zinc-500 uppercase tracking-wider border-b border-zinc-700">
                  <th className="text-left px-4 py-2">Pin</th>
                  <th className="text-left px-4 py-2">Signal</th>
                  <th className="text-left px-4 py-2">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {EXPANSION_SIGNALS.map((pin) => (
                  <tr
                    key={pin.pin}
                    className="hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="px-4 py-2 font-mono text-amber-400 font-bold">
                      {pin.pin}
                    </td>
                    <td className="px-4 py-2 font-mono text-zinc-100">
                      {pin.signal}
                    </td>
                    <td className="px-4 py-2 text-zinc-400">{pin.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Community modules */}
          <div>
            <h4 className="text-sm font-semibold text-zinc-100 mb-3 uppercase tracking-wider">
              Possible Community Modules
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {COMMUNITY_MODULES.map((mod) => (
                <div
                  key={mod.name}
                  className="bg-zinc-900/60 border border-zinc-700/50 rounded-lg px-4 py-3"
                >
                  <h5 className="text-sm font-medium text-amber-400">{mod.name}</h5>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                    {mod.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* License */}
      <section>
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">License</h2>
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-amber-600/15 border border-amber-600/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-6 h-6 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-zinc-100">
                CERN Open Hardware Licence v2 — Strongly Reciprocal
              </h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                All hardware designs, schematics, firmware source, CAD files, and documentation
                are released under the{' '}
                <span className="text-zinc-200 font-medium">CERN-OHL-S v2</span> license.
                You are free to study, modify, manufacture, and distribute this hardware and its
                documentation, provided that any modifications or derivative works are shared under
                the same license.
              </p>
              <p className="text-zinc-500 text-xs font-mono">
                SPDX: CERN-OHL-S-2.0
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section>
        <h2 className="text-2xl font-bold text-zinc-100 mb-4">
          How It Compares
        </h2>
        <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg overflow-hidden overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="border-b border-zinc-700 bg-zinc-800/80">
                <th className="text-left px-5 py-3 text-zinc-500 text-xs uppercase tracking-wider">
                  Feature
                </th>
                <th className="text-left px-5 py-3 text-amber-400 text-xs uppercase tracking-wider font-bold">
                  Super 8 Camera
                </th>
                <th className="text-left px-5 py-3 text-zinc-400 text-xs uppercase tracking-wider">
                  Kodak Super 8 (2023)
                </th>
                <th className="text-left px-5 py-3 text-zinc-400 text-xs uppercase tracking-wider">
                  Vintage Refurb
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {COMPARISON.map((row) => (
                <tr
                  key={row.feature}
                  className="hover:bg-zinc-800/40 transition-colors"
                >
                  <td className="px-5 py-3 text-zinc-300 font-medium whitespace-nowrap">
                    {row.feature}
                  </td>
                  <td className="px-5 py-3 text-zinc-100 font-medium">
                    {row.super8}
                  </td>
                  <td className="px-5 py-3 text-zinc-400">{row.kodak}</td>
                  <td className="px-5 py-3 text-zinc-400">{row.vintage}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
