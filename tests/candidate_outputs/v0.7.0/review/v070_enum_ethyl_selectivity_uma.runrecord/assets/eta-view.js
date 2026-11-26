/*
 * eta-rxncat view components.
 *
 * MIT License. Copyright (c) 2026 the eta-rxncat authors.
 *
 * Plain ES2017, one classic script, no build. It defines window.EtaView:
 *
 *   EtaView.load()  -> the RunData of the page's #run-data element, or null with a message
 *   EtaView.moleculeViewer(element, runData, id)    id: species, frequency or trajectory id;
 *                                                   update(frameIndex)
 *   EtaView.modeAnimator(element, runData, id)      id: frequency id; update(modeIndex)
 *   EtaView.trajectoryPlayer(element, runData, id)  id: trajectory id; update(frameIndex)
 *   EtaView.energyPlot(element, runData, id)        id: trajectory id; update(frameIndex)
 *   EtaView.candidateTable(element, runData, id)    id: candidate id to mark, or null;
 *                                                   update(candidateId)
 *
 * Every component returns {update, destroy}, reads only runData and keeps no global state.
 * A user's step in a player or a plot raises a bubbling "eta-step" event from its element,
 * with detail {trajectoryId, step}; update() never raises one.
 *
 * Text reaches the page only as text nodes and attribute values, never as markup.
 */
(function () {
  "use strict";

  var SCHEMA_VERSION = 1;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var KCAL_MOL_PER_HARTREE = 627.5094740631;
  var MODE_FRAMES = 20;
  var MODE_AMPLITUDE_ANGSTROM = 0.4;
  var PLAY_INTERVAL_MS = 500;
  var MODE_INTERVAL_MS = 60;
  var VIEWER_STYLE = "position:relative;width:420px;max-width:100%;height:320px;" +
    "outline:1px solid #999;margin:1px";
  var CURRENT_COLOR = "#c00000";
  var NOT_RECORDED = "disposition not recorded";
  var USED_TITLE = "Used in the result";
  var NOT_USED_TITLE = "Not used (rejected, merged or superseded)";

  /* --- Small DOM helpers ---------------------------------------------------------------- */

  function make(tag, text, attributes) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    Object.keys(attributes || {}).forEach(function (name) {
      node.setAttribute(name, String(attributes[name]));
    });
    return node;
  }

  function svg(tag, attributes, text) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attributes).forEach(function (name) {
      node.setAttribute(name, String(attributes[name]));
    });
    if (text !== undefined) {
      node.textContent = String(text);
    }
    return node;
  }

  function add(parent) {
    for (var i = 1; i < arguments.length; i += 1) {
      parent.appendChild(arguments[i]);
    }
    return parent;
  }

  function empty(element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }

  function find(list, key, value) {
    for (var i = 0; i < list.length; i += 1) {
      if (list[i][key] === value) {
        return list[i];
      }
    }
    return null;
  }

  function clamp(value, count) {
    var index = Math.round(Number(value));
    if (!(index > 0)) {
      return 0;
    }
    return Math.min(index, Math.max(count - 1, 0));
  }

  function number(value, digits) {
    return value === null || value === undefined ? "not computed" : value.toFixed(digits);
  }

  function message(element, text, className) {
    var node = make("p", text, { "class": className || "warn" });
    element.appendChild(node);
    return node;
  }

  /* A component that has nothing to drive: it only said why. */
  function inert(element) {
    return {
      update: function () {},
      destroy: function () { empty(element); }
    };
  }

  function announce(element, trajectoryId, step) {
    element.dispatchEvent(new CustomEvent("eta-step", {
      bubbles: true,
      detail: { trajectoryId: trajectoryId, step: step }
    }));
  }

  function ordinal(n) {
    var tail = n % 100;
    if (tail >= 11 && tail <= 13) {
      return n + "th";
    }
    return n + (["th", "st", "nd", "rd"][n % 10] || "th");
  }

  /* The index, in the optimizer's count, of the stored frame at position i. */
  function evaluationOf(trajectory, i) {
    if (i === trajectory.frames.length - 1) {
      return trajectory.n_frames_total - 1;
    }
    return i * trajectory.decimation_stride;
  }

  /* --- Dispositions: whether a row fed the result, and why not --------------------------- */

  function atom(symbols, i) {
    return i < symbols.length ? symbols[i] + i : String(i);
  }

  function pair(symbols, i, j) {
    return atom(symbols, i) + "–" + atom(symbols, j);
  }

  function sampleLabel(d, symbols) {
    if (d.kind === "member") {
      return d.weight_fraction === null || d.weight_fraction === undefined ? "member" :
        "member (weight " + d.weight_fraction.toFixed(3) + ")";
    }
    if (d.kind === "merged") {
      return "merged into sample " + d.merged_into_index;
    }
    var reason = d.reason_code || "no reason recorded";
    if (d.clash) {
      reason += " " + pair(symbols, d.clash.i, d.clash.j) + " " +
        d.clash.distance_angstrom.toFixed(3) + " Å";
    }
    var changes = [["formed", d.bonds_formed], ["broken", d.bonds_broken]].filter(function (c) {
      return c[1] && c[1].length;
    }).map(function (c) {
      return c[0] + " " + c[1].map(function (b) { return pair(symbols, b[0], b[1]); }).join(", ");
    });
    if (changes.length) {
      reason += " (" + changes.join("; ") + ")";
    }
    return (d.kind === "excluded" ? "excluded: " : "fell through: ") + reason;
  }

  function endpointLabel(d) {
    if (d.kind === "kept") {
      return "kept";
    }
    if (d.kind === "superseded_by_push") {
      return "superseded by push" + (d.superseded_by_frequency_id ?
        " → " + d.superseded_by_frequency_id : "");
    }
    if (d.kind === "dropped") {
      return "dropped: " + (d.reason_code || "no reason recorded");
    }
    return NOT_RECORDED;
  }

  function symbolsOf(runData, speciesId, fallbackId) {
    var species = find(runData.species, "species_id", speciesId) ||
      find(runData.species, "species_id", fallbackId);
    return species ? species.symbols : [];
  }

  /* Used rows first, otherwise in the given order. */
  function usedFirst(rows) {
    return rows.filter(function (r) { return r.used; }).concat(
      rows.filter(function (r) { return !r.used; }));
  }

  /* The rows of one candidate unit: TS samples, then minima, used rows first. A frequency no
   * disposition names (an older document) is used only when it is a member's. */
  function rowsOf(runData, c) {
    var rows = [];
    var named = {};
    function frequencySymbols(frequencyId) {
      var entry = find(runData.frequencies, "frequency_id", frequencyId);
      return entry ? symbolsOf(runData, entry.species_id, c.species_id) : [];
    }
    (c.sample_dispositions || []).forEach(function (d) {
      var symbols = d.frequency_id ? frequencySymbols(d.frequency_id) :
        symbolsOf(runData, d.template_id, c.species_id);
      named[d.frequency_id] = true;
      rows.push({
        frequencyId: d.frequency_id, ts: true, used: d.kind === "member",
        kind: d.kind.replace("_", " "), label: sampleLabel(d, symbols),
        sampleIndex: d.sample_index, source: d.source, templateId: d.template_id,
        identity: d.identity || null, symbols: symbols
      });
    });
    c.frequency_ids.forEach(function (frequencyId) {
      if (named[frequencyId]) {
        return;
      }
      var member = find(c.members, "frequency_id", frequencyId);
      rows.push({
        frequencyId: frequencyId, ts: true, used: !!member,
        kind: member ? "member" : "not recorded", label: member ? "member" : NOT_RECORDED,
        sampleIndex: member ? member.member_index : null, identity: null, symbols: []
      });
    });
    var endpoints = {};
    (c.endpoint_dispositions || []).forEach(function (d) {
      endpoints[d.frequency_id] = true;
      rows.push({
        frequencyId: d.frequency_id, ts: false, used: d.kind === "kept",
        label: endpointLabel(d), identity: null, symbols: []
      });
    });
    c.endpoint_frequency_ids.forEach(function (frequencyId) {
      if (!endpoints[frequencyId]) {
        rows.push({
          frequencyId: frequencyId, ts: false, used: false, label: NOT_RECORDED,
          identity: null, symbols: []
        });
      }
    });
    return usedFirst(rows);
  }

  /* Every distinct row of one frequency id over all candidate units. */
  function rowsFor(runData, frequencyId) {
    var seen = {};
    var rows = [];
    runData.candidates.forEach(function (c) {
      rowsOf(runData, c).forEach(function (r) {
        if (r.frequencyId === frequencyId && !seen[r.label]) {
          seen[r.label] = true;
          rows.push(r);
        }
      });
    });
    return usedFirst(rows);
  }

  function identityText(identity, symbols) {
    function value(x, digits) {
      return x === null ? "none" : x.toFixed(digits);
    }
    var distances = identity.forming_distances.map(function (d) {
      return pair(symbols, d.i, d.j) + " " + d.distance_angstrom.toFixed(3) + " Å";
    }).join(", ");
    var phase = identity.in_phase_bool === null ? "not evaluated" :
      identity.in_phase_bool ? "yes" : "no";
    return "Identity: imaginary frequency " + value(identity.imaginary_frequency_cm1, 1) +
      " cm⁻¹; forming-bond overlap " + value(identity.forming_overlap, 3) +
      "; active-core KE fraction " + value(identity.active_core_ke_fraction, 3) +
      "; forming distances " + distances + "; in phase " + phase + "; " +
      (identity.passed_bool ? "pass" : "FAIL (" + identity.reason_codes.join(", ") + ")");
  }

  /* The disposition and identity numbers of a frequency id, appended to element. */
  function showDisposition(element, rows) {
    rows.forEach(function (r) {
      element.appendChild(make("p", "Disposition: " + r.label, { "class": "eta-disposition" }));
      if (r.identity) {
        element.appendChild(make("p", identityText(r.identity, r.symbols),
          { "class": "eta-identity" }));
      }
    });
  }

  /* --- 3Dmol ---------------------------------------------------------------------------- */

  function xyzBlock(symbols, coordinates) {
    var lines = [String(symbols.length), ""];
    for (var i = 0; i < symbols.length; i += 1) {
      var r = coordinates[i];
      lines.push(symbols[i] + " " + r[0].toFixed(6) + " " + r[1].toFixed(6) + " " +
        r[2].toFixed(6));
    }
    return lines.join("\n") + "\n";
  }

  function styleViewer(viewer) {
    viewer.setStyle({}, { stick: { radius: 0.12 }, sphere: { scale: 0.25 } });
  }

  /* Return a viewer in a new box inside element, or null (with a message) without WebGL. */
  function openViewer(element) {
    var box = make("div", null, { "class": "eta-3d", style: VIEWER_STYLE });
    element.appendChild(box);
    var viewer = null;
    try {
      viewer = window.$3Dmol.createViewer(box, { backgroundColor: "white" });
    } catch (error) {
      viewer = null;
    }
    if (!viewer) {
      element.removeChild(box);
      message(element, "The 3D viewer needs WebGL, which this browser did not provide.");
      return null;
    }
    return {
      viewer: viewer,
      close: function () {
        viewer.stopAnimate();
        /* 3Dmol 2.5.5 has no destroy: its observers and window listener would draw the
         * removed viewer at size zero, which fails on the canvas all viewers share. */
        [viewer.divwatcher, viewer.intwatcher].forEach(function (watcher) {
          if (watcher) {
            watcher.disconnect();
          }
        });
        viewer.show = function () {};
        viewer.clear();
        /* Give the WebGL context back: browsers allow only a few at a time. */
        Array.prototype.forEach.call(box.querySelectorAll("canvas"), function (canvas) {
          var gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
          var loser = gl && gl.getExtension("WEBGL_lose_context");
          if (loser) {
            loser.loseContext();
          }
        });
        if (box.parentNode) {
          box.parentNode.removeChild(box);
        }
      }
    };
  }

  /* --- moleculeViewer ------------------------------------------------------------------- */

  function structuresOf(runData, id) {
    var species = find(runData.species, "species_id", id);
    if (species) {
      return { species: species, list: [species.coordinates_angstrom] };
    }
    var frequency = find(runData.frequencies, "frequency_id", id);
    if (frequency && frequency.status === "completed") {
      return {
        species: find(runData.species, "species_id", frequency.species_id),
        list: [frequency.coordinates_angstrom]
      };
    }
    var trajectory = find(runData.trajectories, "trajectory_id", id);
    if (trajectory && trajectory.status === "stored" && trajectory.frames.length) {
      return {
        species: find(runData.species, "species_id", trajectory.species_id),
        list: trajectory.frames.map(function (f) { return f.coordinates_angstrom; })
      };
    }
    return null;
  }

  function moleculeViewer(element, runData, id) {
    empty(element);
    var structures = structuresOf(runData, id);
    if (!structures) {
      message(element, "No structure is stored for " + id + ".");
      return inert(element);
    }
    showDisposition(element, rowsFor(runData, id));
    var view = openViewer(element);
    if (!view) {
      return inert(element);
    }
    function show(index) {
      var coordinates = structures.list[clamp(index, structures.list.length)];
      view.viewer.removeAllModels();
      view.viewer.addModel(xyzBlock(structures.species.symbols, coordinates), "xyz");
      styleViewer(view.viewer);
      view.viewer.render();
    }
    show(0);
    view.viewer.zoomTo();
    view.viewer.render();
    return {
      update: show,
      destroy: function () {
        view.close();
        empty(element);
      }
    };
  }

  /* --- modeAnimator --------------------------------------------------------------------- */

  /* MODE_FRAMES geometries of one period; the most displaced atom reaches the amplitude. */
  function modeFrames(coordinates, displacements) {
    var largest = displacements.reduce(function (size, d) {
      return Math.max(size, Math.hypot(d[0], d[1], d[2]));
    }, 0);
    var scale = largest > 0 ? MODE_AMPLITUDE_ANGSTROM / largest : 0;
    var frames = [];
    for (var k = 0; k < MODE_FRAMES; k += 1) {
      var phase = scale * Math.sin(2 * Math.PI * k / MODE_FRAMES);
      frames.push(coordinates.map(function (r, i) {
        return [0, 1, 2].map(function (axis) {
          return r[axis] + phase * displacements[i][axis];
        });
      }));
    }
    return frames;
  }

  /* A minimum should have no imaginary mode; any other frequency is a transition state's. */
  function expectedImaginary(runData, frequencyId) {
    var minimum = runData.candidates.some(function (c) {
      return c.endpoint_frequency_ids.indexOf(frequencyId) !== -1;
    });
    return minimum ? 0 : 1;
  }

  function modeAnimator(element, runData, id) {
    empty(element);
    var entry = find(runData.frequencies, "frequency_id", id);
    var rows = rowsFor(runData, id);
    if (!entry || entry.status !== "completed") {
      showDisposition(element, rows);
      var why = !entry ? "unknown" : entry.status === "failed" ?
        "failed: " + entry.failed_code : "missing from the store";
      message(element, "Frequencies " + why + ". The imaginary-mode count is unknown.");
      return inert(element);
    }
    var species = find(runData.species, "species_id", entry.species_id);
    var expected = expectedImaginary(runData, id);
    element.appendChild(make("p", species.label, { "class": "eta-species" }));
    showDisposition(element, rows);
    var problems = [];
    if (entry.n_imaginary !== expected) {
      problems.push(entry.n_imaginary + " imaginary mode(s); expected " + expected + ".");
    }
    rows.forEach(function (r) {
      if (r.identity && !r.identity.passed_bool) {
        problems.push("Identity check failed: " + r.identity.reason_codes.join(", ") + ".");
      }
    });
    if (problems.length) {
      element.appendChild(make("div", "WARNING: " + problems.join(" "), { "class": "banner" }));
    }
    var readout = make("p", null, { "class": "eta-mode" });
    var buttons = make("p");
    add(element, readout, buttons);
    var view = openViewer(element);
    if (!view) {
      return inert(element);
    }
    var modes = entry.imaginary_modes;
    var zoomed = false;
    function show(index) {
      var viewer = view.viewer;
      var chosen = clamp(index, modes.length);
      viewer.stopAnimate();
      viewer.removeAllModels();
      if (!modes.length) {
        readout.textContent = "No imaginary mode.";
        viewer.addModel(xyzBlock(species.symbols, entry.coordinates_angstrom), "xyz");
        styleViewer(viewer);
      } else {
        readout.textContent = "Imaginary mode " + (chosen + 1) + " of " + modes.length + ": " +
          modes[chosen].frequency_cm1.toFixed(1) + " cm-1 (largest displacement " +
          MODE_AMPLITUDE_ANGSTROM + " Å)";
        var frames = modeFrames(entry.coordinates_angstrom, modes[chosen].displacements_angstrom);
        viewer.addModelsAsFrames(frames.map(function (f) {
          return xyzBlock(species.symbols, f);
        }).join(""), "xyz");
        styleViewer(viewer);
      }
      if (!zoomed) {
        viewer.zoomTo();
        zoomed = true;
      }
      viewer.render();
      if (modes.length) {
        viewer.animate({ loop: "forward", interval: MODE_INTERVAL_MS });
      }
    }
    if (modes.length > 1) {
      modes.forEach(function (mode, i) {
        var button = make("button", "Mode " + (i + 1), { type: "button" });
        button.addEventListener("click", function () { show(i); });
        buttons.appendChild(button);
      });
    }
    show(0);
    return {
      update: show,
      destroy: function () {
        view.close();
        empty(element);
      }
    };
  }

  /* --- trajectoryPlayer ----------------------------------------------------------------- */

  function convergenceText(c) {
    var parts = [c.converged_bool ? "converged" : "not converged: " + c.failed_code];
    if (c.n_steps !== null) {
      parts.push(c.n_steps + " steps");
    }
    if (c.n_engine_calls !== null) {
      parts.push(c.n_engine_calls + " engine calls");
    }
    if (c.final_energy_hartree !== null) {
      parts.push("final energy " + c.final_energy_hartree.toFixed(8) + " Eh");
    }
    if (c.final_max_gradient_hartree_per_bohr !== null) {
      parts.push("final max gradient " +
        c.final_max_gradient_hartree_per_bohr.toExponential(2) + " Eh/Bohr");
    }
    if (c.recovery_steps.length) {
      parts.push("recovery: " + c.recovery_steps.join(", "));
    }
    return "Convergence: " + parts.join("; ") + ".";
  }

  function acceptance(value) {
    if (value === null) {
      return "acceptance not recorded";
    }
    return value ? "accepted" : "rejected";
  }

  /* Say why a trajectory has nothing to show; return the trajectory when it has frames. */
  function framesOf(element, runData, id) {
    var trajectory = find(runData.trajectories, "trajectory_id", id);
    if (!trajectory || trajectory.status !== "stored") {
      message(element, "Trajectory " + (trajectory ? "missing from the store" : "unknown") + ".");
      return null;
    }
    if (!trajectory.frames.length) {
      message(element, "No trajectory stored. " + convergenceText(trajectory.convergence));
      return null;
    }
    return trajectory;
  }

  function trajectoryPlayer(element, runData, id) {
    empty(element);
    var trajectory = framesOf(element, runData, id);
    if (!trajectory) {
      return inert(element);
    }
    var frames = trajectory.frames;
    var step = 0;
    var timer = null;
    element.appendChild(make("p", trajectory.kind + ": " + trajectory.label,
      { "class": "eta-label" }));
    if (trajectory.decimation_stride > 1) {
      element.appendChild(make("p", "decimated: every " +
        ordinal(trajectory.decimation_stride) + " of " + trajectory.n_frames_total,
        { "class": "warn eta-decimated" }));
    }
    element.appendChild(make("p", convergenceText(trajectory.convergence),
      { "class": "eta-convergence" }));
    var stage = make("div");
    element.appendChild(stage);
    var molecule = moleculeViewer(stage, runData, id);
    var play = make("button", "Play", { type: "button" });
    var slider = make("input", null, {
      type: "range", min: 0, max: frames.length - 1, step: 1, "aria-label": "Frame"
    });
    var readout = make("span", null, { "class": "eta-readout" });
    add(element, add(make("p"), play, slider, readout));

    function show(index) {
      step = clamp(index, frames.length);
      var frame = frames[step];
      slider.value = String(step);
      readout.textContent = " frame " + (step + 1) + " of " + frames.length + " (step " +
        evaluationOf(trajectory, step) + "); " + acceptance(frame.accepted_bool) +
        (frame.ladder_step === null ? "" : "; " + frame.ladder_step) + "; E = " +
        frame.energy_hartree.toFixed(8) + " Eh; max gradient " +
        frame.max_gradient_hartree_per_bohr.toExponential(2) + " Eh/Bohr";
      molecule.update(step);
    }
    function pause() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
      play.textContent = "Play";
    }
    function userStep(index) {
      show(index);
      announce(element, id, step);
    }
    play.addEventListener("click", function () {
      if (timer !== null) {
        pause();
        return;
      }
      if (step >= frames.length - 1) {
        userStep(0);
      }
      play.textContent = "Pause";
      timer = window.setInterval(function () {
        if (step < frames.length - 1) {
          userStep(step + 1);
        }
        if (step >= frames.length - 1) {
          pause();
        }
      }, PLAY_INTERVAL_MS);
    });
    slider.addEventListener("input", function () {
      pause();
      userStep(slider.value);
    });
    show(0);
    return {
      update: show,
      destroy: function () {
        pause();
        molecule.destroy();
        empty(element);
      }
    };
  }

  /* --- energyPlot ----------------------------------------------------------------------- */

  function energyPlot(element, runData, id) {
    empty(element);
    var trajectory = framesOf(element, runData, id);
    if (!trajectory) {
      return inert(element);
    }
    var width = 460;
    var height = 240;
    var left = 70;
    var right = 15;
    var top = 25;
    var bottom = 40;
    var frames = trajectory.frames;
    var energies = frames.map(function (f) {
      return (f.energy_hartree - frames[0].energy_hartree) * KCAL_MOL_PER_HARTREE;
    });
    var low = energies.reduce(function (a, b) { return Math.min(a, b); });
    var high = energies.reduce(function (a, b) { return Math.max(a, b); });
    var last = evaluationOf(trajectory, frames.length - 1);

    function x(i) {
      return left + (last ? evaluationOf(trajectory, i) / last : 0.5) * (width - left - right);
    }
    function y(i) {
      var share = high > low ? (energies[i] - low) / (high - low) : 0.5;
      return height - bottom - share * (height - top - bottom);
    }

    var plot = svg("svg", {
      viewBox: "0 0 " + width + " " + height, width: width, height: height,
      role: "img", "aria-label": "Energy against step", style: "max-width:100%;font-size:11px"
    });
    var axes = "M" + left + " " + top + " V" + (height - bottom) + " H" + (width - right);
    add(plot,
      svg("path", { d: axes, fill: "none", stroke: "#333" }),
      svg("text", { x: 4, y: 14 }, "E - E(first frame) / kcal mol-1"),
      svg("text", { x: left - 6, y: top + 4, "text-anchor": "end" }, high.toFixed(2)),
      svg("text", { x: left - 6, y: height - bottom, "text-anchor": "end" }, low.toFixed(2)),
      svg("text", { x: left, y: height - bottom + 14, "text-anchor": "middle" }, "0"),
      svg("text", { x: width - right, y: height - bottom + 14, "text-anchor": "end" }, last),
      svg("text", { x: (left + width - right) / 2, y: height - 8, "text-anchor": "middle" },
        "step"),
      svg("polyline", {
        points: frames.map(function (f, i) { return x(i) + "," + y(i); }).join(" "),
        fill: "none", stroke: "#1f5fa8", "stroke-width": 1.5
      }));
    var marker = svg("circle", {
      r: 6, fill: "none", stroke: CURRENT_COLOR, "stroke-width": 2.5, "class": "eta-current"
    });
    function show(index) {
      var step = clamp(index, frames.length);
      marker.setAttribute("cx", String(x(step)));
      marker.setAttribute("cy", String(y(step)));
      marker.setAttribute("data-step", String(step));
    }
    frames.forEach(function (frame, i) {
      var point = svg("circle", {
        cx: x(i), cy: y(i), r: 3.5, fill: "#1f5fa8", "class": "eta-point", "data-step": i,
        style: "cursor:pointer"
      });
      point.appendChild(svg("title", {}, "step " + evaluationOf(trajectory, i) + ": " +
        frame.energy_hartree.toFixed(8) + " Eh"));
      point.addEventListener("click", function () {
        show(i);
        announce(element, id, i);
      });
      plot.appendChild(point);
    });
    plot.appendChild(marker);
    element.appendChild(plot);
    show(0);
    return {
      update: show,
      destroy: function () { empty(element); }
    };
  }

  /* --- candidateTable ------------------------------------------------------------------- */

  function candidateLink(candidateId) {
    return make("a", candidateId, { href: "#c/" + encodeURIComponent(candidateId) });
  }

  function gateBadge(gate) {
    var verdict = gate.pass_bool ? "pass" : "fail";
    var text = gate.gate_id + ": " + verdict.toUpperCase();
    if (gate.value !== null) {
      text += " value " + gate.value;
    }
    if (gate.threshold !== null) {
      text += " threshold " + gate.threshold;
    }
    if (gate.unit !== null) {
      text += " " + gate.unit;
    }
    if (gate.detail_code !== null) {
      text += " [" + gate.detail_code + "]";
    }
    return make("span", text, { "class": "badge " + verdict });
  }

  /* One column: its title, the sort value of a unit, and the cell's content. */
  function columns(runData) {
    function text(title, of) {
      return { title: title, value: of, cell: of };
    }
    function measure(title, key, digits) {
      return {
        title: title,
        value: function (c) { return c[key]; },
        cell: function (c) { return number(c[key], digits); }
      };
    }
    function imaginary(c) {
      return rowsOf(runData, c).filter(function (r) {
        return r.ts && r.frequencyId;
      }).map(function (r) {
        var entry = find(runData.frequencies, "frequency_id", r.frequencyId);
        return (entry.status === "completed" ? entry.n_imaginary : entry.status) +
          " (" + r.kind + ")";
      }).join(", ") || "none";
    }
    function gatesOf(c) {
      return runData.gates.filter(function (g) {
        return g.candidate_entry_id === c.candidate_entry_id;
      });
    }
    return [
      {
        title: "Candidate",
        value: function (c) { return c.candidate_id; },
        cell: function (c) { return candidateLink(c.candidate_id); }
      },
      text("R", function (c) {
        return Object.keys(c.entry_ids_by_site).sort().map(function (site) {
          return site + "=" + c.entry_ids_by_site[site];
        }).join(", ");
      }),
      text("Pathway", function (c) { return c.pathway; }),
      text("Engine", function (c) { return c.engine_id; }),
      text("Charge / multiplicity", function (c) {
        return c.charge + " / " + c.spin_multiplicity;
      }),
      {
        title: "Rank used",
        value: function (c) { return c.template_rank_used; },
        cell: function (c) {
          return c.template_rank_used === null ? "none" : c.template_rank_used;
        }
      },
      text("Fallbacks", function (c) {
        var parts = c.fallback_attempts.map(function (a) {
          return "rank " + a.rank + " " + a.template_id + ": " + a.outcome +
            (a.reason_code === null ? "" : " (" + a.reason_code + ")");
        }).concat(c.graft_refusals.map(function (r) {
          return "graft " + r.template_id + " " + r.site_id + "=" + r.entry_id + ": refused (" +
            r.reason_code + ")";
        }));
        if (c.stop_reason_code !== null) {
          parts.push("stopped: " + c.stop_reason_code);
        }
        if (c.stall_cap_reached_bool) {
          parts.push("stall cap reached");
        }
        return parts.join("; ") || "none";
      }),
      measure("ΔG‡ / kcal mol-1", "dG_dagger_kcal_mol", 2),
      measure("ΔΔG‡ / kcal mol-1", "ddG_dagger_kcal_mol", 2),
      text("Members (weight)", function (c) {
        return c.members.map(function (m) {
          return m.member_index + " " + m.source + " (" + m.weight_fraction.toFixed(3) + ")";
        }).join(", ") || "none";
      }),
      measure("Graft RMSD / Å", "graft_rmsd_angstrom", 3),
      text("TS imaginary modes", imaginary),
      {
        title: "Gates",
        value: function (c) {
          return gatesOf(c).filter(function (g) { return !g.pass_bool; }).length;
        },
        cell: function (c) {
          var cell = document.createDocumentFragment();
          gatesOf(c).forEach(function (g) { cell.appendChild(gateBadge(g)); });
          return cell.firstChild ? cell : "no gates";
        }
      }
    ];
  }

  /* Numbers by size, text by locale; a missing value is always last. */
  function compare(a, b, direction) {
    if (a === null || b === null) {
      return (a === null ? 1 : 0) - (b === null ? 1 : 0);
    }
    if (typeof a === "number" && typeof b === "number") {
      return direction * (a - b);
    }
    return direction * String(a).localeCompare(String(b));
  }

  function candidateTable(element, runData, id) {
    empty(element);
    var all = columns(runData);
    var sorted = null;
    var direction = 1;
    var marked = id;
    var table = make("table", null, { "class": "eta-candidates" });
    var head = make("tr");
    var body = make("tbody");
    var headers = all.map(function (column, i) {
      var button = make("button", column.title, { type: "button" });
      button.addEventListener("click", function () {
        direction = sorted === i ? -direction : 1;
        sorted = i;
        draw();
      });
      var header = add(make("th"), button);
      head.appendChild(header);
      return header;
    });
    function draw() {
      var rows = runData.candidates.slice();
      if (sorted !== null) {
        rows.sort(function (a, b) {
          return compare(all[sorted].value(a), all[sorted].value(b), direction);
        });
      }
      headers.forEach(function (header, i) {
        header.setAttribute("aria-sort", i !== sorted ? "none" :
          direction > 0 ? "ascending" : "descending");
      });
      empty(body);
      rows.forEach(function (candidate) {
        var row = make("tr");
        if (candidate.candidate_id === marked) {
          row.setAttribute("style", "outline:2px solid " + CURRENT_COLOR);
        }
        all.forEach(function (column) {
          var content = column.cell(candidate);
          var cell = make("td");
          cell.appendChild(typeof content === "object" ? content :
            document.createTextNode(String(content)));
          row.appendChild(cell);
        });
        body.appendChild(row);
      });
    }
    draw();
    var scroller = make("div", null, { style: "overflow-x:auto" });
    add(element, add(scroller, add(table, add(make("thead"), head), body)));
    return {
      update: function (candidateId) {
        marked = candidateId;
        draw();
      },
      destroy: function () { empty(element); }
    };
  }

  /* --- Loading and the bundle page ------------------------------------------------------ */

  function refuse(text) {
    document.body.insertBefore(make("p", text, { "class": "banner", id: "eta-load-error" }),
      document.body.firstChild);
    return null;
  }

  function load() {
    var runData;
    try {
      runData = JSON.parse(document.getElementById("run-data").textContent);
    } catch (error) {
      return refuse("The run-data of this page cannot be read.");
    }
    if (!runData || runData.schema_version !== SCHEMA_VERSION) {
      return refuse("unsupported run-data version " +
        String(runData ? runData.schema_version : runData));
    }
    return runData;
  }

  /* A labelled <select> over [id, text, group] options (the group is optional; options of one
   * group are adjacent); onChange gets the chosen id. */
  function chooser(element, title, options, onChange) {
    var select = make("select", null, { style: "max-width:100%" });
    var group = null;
    options.forEach(function (option) {
      if (option[2] && (!group || group.label !== option[2])) {
        group = make("optgroup", null, { label: option[2] });
        select.appendChild(group);
      }
      (option[2] ? group : select).appendChild(make("option", option[1], { value: option[0] }));
    });
    select.addEventListener("change", function () { onChange(select.value); });
    add(element, add(make("label", title + " "), select));
  }

  /* What a frequency row is called: its member or sample index (if any) and its key. */
  function rowName(member, row, key) {
    if (member) {
      return "member " + member.member_index + ", sample " + key;
    }
    return row.ts && row.sampleIndex !== null ?
      "sample " + row.sampleIndex + ", " + key : "sample " + key;
  }

  /* The panels of one candidate: modes on the left, the player above the plot on the right. */
  function candidatePanels(element, runData, candidateId) {
    var found = [];
    var unrun = [];
    var trajectories = [];
    runData.candidates.forEach(function (c) {
      if (c.candidate_id !== candidateId) {
        return;
      }
      var unit = c.pathway + ", " + c.engine_id.split("|")[0];
      rowsOf(runData, c).forEach(function (r) {
        if (!r.frequencyId) {
          unrun.push(unit + ": sample " + r.sampleIndex + " (" + r.source + ", template " +
            r.templateId + "): " + r.label);
          return;
        }
        var entry = find(runData.frequencies, "frequency_id", r.frequencyId);
        var species = find(runData.species, "species_id", entry.species_id);
        var member = r.ts ? find(c.members, "frequency_id", r.frequencyId) : null;
        found.push({
          used: r.used,
          option: [r.frequencyId, unit + ": " + (r.ts ? "TS" : "minimum") + " " + species.label +
            " (" + rowName(member, r, entry.stage_key.slice(0, 12)) + ") — " + r.label,
            r.used ? USED_TITLE : NOT_USED_TITLE]
        });
      });
      c.trajectory_ids.concat(c.endpoint_trajectory_ids).forEach(function (trajectoryId) {
        var t = find(runData.trajectories, "trajectory_id", trajectoryId);
        trajectories.push([trajectoryId, unit + ": " + t.kind + " " + t.label + " (" +
          t.stage_key.slice(0, 12) + ")"]);
      });
    });

    var frequencies = usedFirst(found).map(function (f) { return f.option; });

    empty(element);
    var left = make("div", null, { "class": "eta-left", style: "flex:1 1 440px" });
    var right = make("div", null, { "class": "eta-right", style: "flex:1 1 480px" });
    add(element, add(make("div", null, {
      style: "display:flex;flex-wrap:wrap;gap:1.5em;align-items:flex-start"
    }), left, right));
    var modeStage = make("div");
    var playerStage = make("div", null, { "class": "eta-player" });
    var plotStage = make("div", null, { "class": "eta-plot" });
    var mode = null;
    var player = null;
    var plot = null;

    function showFrequency(frequencyId) {
      if (mode) {
        mode.destroy();
      }
      mode = modeAnimator(modeStage, runData, frequencyId);
    }
    function showTrajectory(trajectoryId) {
      if (player) {
        player.destroy();
        plot.destroy();
      }
      player = trajectoryPlayer(playerStage, runData, trajectoryId);
      plot = energyPlot(plotStage, runData, trajectoryId);
    }
    playerStage.addEventListener("eta-step", function (event) {
      plot.update(event.detail.step);
    });
    plotStage.addEventListener("eta-step", function (event) {
      player.update(event.detail.step);
    });

    if (frequencies.length) {
      chooser(left, "Frequencies", frequencies, showFrequency);
      left.appendChild(modeStage);
      showFrequency(frequencies[0][0]);
    } else {
      message(left, "No frequencies for this candidate.");
    }
    if (unrun.length) {
      var list = make("ul", null, { "class": "eta-unrun" });
      unrun.forEach(function (line) { list.appendChild(make("li", line)); });
      add(left, make("p", "Samples without frequencies (" + NOT_USED_TITLE + "):"), list);
    }
    if (trajectories.length) {
      chooser(right, "Optimization", trajectories, showTrajectory);
      add(right, playerStage, plotStage);
      showTrajectory(trajectories[0][0]);
    } else {
      message(right, "No optimization trajectories for this candidate.");
    }
    return {
      destroy: function () {
        [mode, player, plot].forEach(function (part) {
          if (part) {
            part.destroy();
          }
        });
        empty(element);
      }
    };
  }

  /* The candidate named by a "#c/<id>" fragment, or null. */
  function routed(hash) {
    var fragment = hash.slice(1);
    try {
      fragment = decodeURIComponent(fragment);
    } catch (error) {
      return null;
    }
    return fragment.slice(0, 2) === "c/" ? fragment.slice(2) : null;
  }

  /* Fill the bundle page: the sortable index, and the viewers of one candidate at a time. */
  function start() {
    var panels = Array.prototype.slice.call(document.querySelectorAll(".eta-panels"));
    var runData = load();
    if (!runData) {
      return;
    }
    var index = make("div", null, { id: "eta-index" });
    document.body.insertBefore(index, document.querySelector("body > table"));
    var table = candidateTable(index, runData, null);
    var shown = null;
    var current = null;

    function route() {
      var wanted = routed(window.location.hash);
      var panel = null;
      panels.forEach(function (p) {
        if (p.getAttribute("data-candidate") === wanted) {
          panel = p;
        }
      });
      var target = panel || shown || panels[0];
      if (!target) {
        return;
      }
      if (target !== shown) {
        if (current) {
          current.destroy();
        }
        panels.forEach(function (p) {
          if (p !== target) {
            empty(p);
            var link = candidateLink(p.getAttribute("data-candidate"));
            link.textContent = "Show the 3D viewers of this candidate";
            p.appendChild(link);
          }
        });
        shown = target;
        current = candidatePanels(target, runData, target.getAttribute("data-candidate"));
        table.update(target.getAttribute("data-candidate"));
      }
      if (panel) {
        panel.parentNode.scrollIntoView();
      }
    }
    window.addEventListener("hashchange", route);
    route();
  }

  window.EtaView = {
    load: load,
    moleculeViewer: moleculeViewer,
    modeAnimator: modeAnimator,
    trajectoryPlayer: trajectoryPlayer,
    energyPlot: energyPlot,
    candidateTable: candidateTable
  };

  if (document.getElementById("run-data")) {
    start();
  }
}());
