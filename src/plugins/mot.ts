import { JsPsych, JsPsychPlugin, ParameterType, TrialType } from "jspsych";
import {
    createTimeline,
    engine,
} from 'animejs';

engine.defaults.autoplay = false;
engine.defaults.onBegin = self => console.log(`started: ${self.id}`);
engine.defaults.onComplete = self => console.log(`finished: ${self.id}`);

export type ValidTask = "PROBE" | "LOCERROR"


const info = <const>{
    name: "MOT",
    parameters: {
        scene: {
            // BOOL, STRING, INT, FLOAT, FUNCTION, KEY, KEYS, SELECT, HTML_STRING,
            // IMAGE, AUDIO, VIDEO, OBJECT, COMPLEX
            type: ParameterType.STRING,
            description: "The json-serialized string encoding motion frames." +
                " The string should decode into an array of arrays, where the first" +
                " dimension denotes the number of time steps, and the second dimension" +
                " denotes the state for each object.",
        },
        targets: {
            type: ParameterType.INT,
            description: "The first N objects in `scene` are denoted as targets."
        },
        object_class: {
            type: ParameterType.STRING,
            description: "The css class describing object appearance.",
        },
        target_class: {
            type: ParameterType.STRING,
            description: "The css class describing target appearance.",
        },
        probe_class: {
            type: ParameterType.STRING,
            description: "The css class describing probe appearance.",
        },
        probe_steps: {
            type: ParameterType.INT,
            default: 2,
            description: "Number of frames for probe to appear.",
        },
        display_height: {
            type: ParameterType.INT,
            description: "The display height in pixels.",
        },
        display_width: {
            type: ParameterType.INT,
            description: "The display width in pixels",
        },
        flip_height: {
            type: ParameterType.BOOL,
            description: "Flip the y coordinates.",
        },
        flip_width: {
            type: ParameterType.BOOL,
            description: "Flip the x coordinates.",
        },
        step_dur: {
            type: ParameterType.FLOAT,
            default: 41.67,
            description: "Duration of a single step in the motion phase (in ms).",
        },
        premotion_dur: {
            type: ParameterType.FLOAT,
            default: 3000.0,
            description: "The duration of the pre-motion phase (in ms).",
        },
        response_dur: {
            type: ParameterType.FLOAT,
            default: Infinity,
            description: "The duration of the response phase (in ms).",
        },
        task: {
            type: ParameterType.STRING,
            default: "PROBE",
            description: "Collect target designations",
        },
        effort_dial: {
            type: ParameterType.BOOL,
            default: false,
            description: "Display and collect responses from a dynamic effort dial.",
        },
        world_scale: {
            type: ParameterType.FLOAT,
            default: 1.0,
            description: "Scaling factor for object trajectories.",
        },
    },
};

type Info = typeof info;

/**
 * **MOT**
 *
 * Track objects with your mind!
 *
 * @author Mario Belledonne
 * @see {@link https://DOCUMENTATION_URL DOCUMENTATION LINK TEXT}
 */
class MOTPlugin implements JsPsychPlugin<Info> {
    static info = info;

    constructor(private jsPsych: JsPsych) { }

    trial(display_element: HTMLElement, trial: TrialType<Info>) {
        /**
         * SETUP
         */

        // VARIABLE DECLARATIONS
        const scene = JSON.parse(trial.scene);
        const state = scene.positions;
        const n_objects = state[0].length;
        const obj_elems = Array<HTMLElement>(n_objects);
        const selected = Array<Boolean>(n_objects);
        let mot_prompt: HTMLElement;
        const effort_dial = [];
        let start_time: number = 0.0;
        const tot_dur = trial.step_dur * state.length;
        // pixels per world unit
        const world_to_display = trial.display_width / trial.world_scale;
        // assuming objects are 40 units -> how many pixels
        const obj_dim = 40.0 * world_to_display; // REVIEW
        const probe_dim = 5.0 * world_to_display; // REVIEW
        const screen_width = document.getElementsByTagName('body')[0].offsetWidth;

        // probe element
        const probe_elem = document.createElement("span");
        probe_elem.id = "probe";
        probe_elem.className = trial.probe_class;
        display_element.appendChild(probe_elem);

        // audio for effort dial
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const gain = audioCtx.createGain();
        const oscillator = audioCtx.createOscillator();

        // ELEMENTS
        let mot_el = document.createElement("div");
        mot_el.className = "mot-div";
        mot_el.style = `width:${trial.display_width}px;height:${trial.display_height}px`;
        display_element.appendChild(mot_el);

        // mot prompt
        if (trial.target_designation) {
            mot_prompt = document.createElement("div");
            mot_prompt.className = "jspsych-top";
            // mot_prompt.className = "mot-prompt";
            mot_prompt.style = "color:white";
            mot_prompt.innerHTML = `Please select ${trial.targets} objects`;
            display_element.appendChild(mot_prompt);
        }

        // initialize animation timeline
        let tl = createTimeline({
            defaults: {
                ease: 'linear',
            },
            autoplay: false,
            // add prompt at end of animation
            onComplete : () => {
                // effort dial
                if (trial.effort_dial) {
                    document.removeEventListener("mousemove", update_effort_dial);
                    oscillator.stop();
                    gain.disconnect(audioCtx.destination);
                }


                // viz prompt
                if (trial.target_designation) {
                    mot_prompt.style = "color:black";
                } else {
                    allow_next();
                }
            },
        });

        const t_pos = (xy: Array<number>, dim:number = obj_dim) => {
            let [x, y] = xy;
            if (trial.flip_width) {
                x = -x;
            }
            if (trial.flip_height) {
                y = -y;
            }
            // x is already the same space (+-0)
            let tx = x;
            // y goes from ([-dy, +dy]) -> ([0, 2dy])
            let ty = -y + (0.5 * (trial.display_height - dim));
            return ([tx, ty]);
        };


        // populate scene with objects
        for (let i = 0; i < obj_elems.length; i++) {
            const css_cls = (i < trial.targets) ? trial.target_class : trial.object_class
            const obj_el = document.createElement("span");
            obj_el.className = css_cls;
            // initial positoins of objects
            let [x, y] = t_pos(state[0][i].slice(0, 2));
            obj_el.setAttribute("style",
                                `width:${obj_dim}px;height:${obj_dim}px;` +
                `transform:translateX(${x}px) translateY(${y}px);`);
            obj_el.id = `obj_${i}`;
            // optionally add object selection
            if (trial.target_designation) {
                obj_el.addEventListener("click", () => {
                    if (tl.completed) {
                        selected[i] = !(selected[i]);
                        obj_el.className = selected[i] ?
                            trial.target_class : trial.object_class;
                        // after a click - check if enough objects are selected
                        after_response();
                    }
                });
            }
            // store info
            mot_el.appendChild(obj_el);
            obj_elems[i] = obj_el;
            selected[i] = false;
        }

        // create next button
        // enabled after motion, optionally after enough selections
        var btn_el: HTMLButtonElement = document.createElement("button");
        btn_el.className = "jspsych-btn";
        btn_el.id = "resp_btn";
        btn_el.disabled = true;
        btn_el.style = "margin:10px";
        btn_el.innerHTML = "Next"
        btn_el.addEventListener("click", (_) => { end_trial(); });
        display_element.appendChild(btn_el);


        // motion phase
        for (let i = 0; i < n_objects; i++) {
            const positions = state.map(frame => t_pos(frame[i].slice(0, 2)));
            const xs = positions.map(f => ({
                to: f[0],
                duration: trial.step_dur
            }));
            const ys = positions.map(f => ({
                to: f[1],
                duration: trial.step_dur
            }));
            // motion begins at end of `premotion_dur`
            tl.add(obj_elems[i], {x: xs, y: ys}, 0);
        }

        // probes
        const probe_anim = (frame: number, obj_id: number) => {
            const obj = obj_elems[obj_id - 1];
            const positions = state
                .slice(frame, frame + trial.probe_steps)
                .map(ps => t_pos(ps[obj_id].slice(0, 2), probe_dim));
            const xs = positions.map(f => ({
                to: f[0],
                duration: trial.step_dur
            }));
            const ys = positions.map(f => ({
                to: f[1],
                duration: trial.step_dur
            }));
            const probe_start = frame * trial.step_dur;
            const probe_stop = probe_start + trial.probe_steps * trial.step_dur;
            tl.set(probe_elem, {
                x: positions[0][0],
                y: positions[0][1],
                opacity: 1,
            }, probe_start)
            tl.add(probe_elem, {x: xs, y:ys}, probe_start);
            tl.set(probe_elem, {opacity: 0}, probe_stop)
        };
        if (scene.hasOwnProperty('probes')) {
            const probes = scene.probes;
            for (let probe_frame of probes) {
                console.log(probe_frame);
                const [frame, obj_id] = probe_frame;
                probe_anim(frame, obj_id);
            }
        }



        // target designation phase
        // `after_response` is called whenever an object is clicked.
        // if enough objects are selected, the `next` button will appear.
        const after_response = () => {
            if (tl.completed) {
                // check for minimum number of selections
                if (selected.filter(Boolean).length >= trial.targets) {
                    allow_next();
                } else {
                    disable_next();
                }
            }
        };

        // pre-motion phase
        // indicate targets
        this.jsPsych.pluginAPI.setTimeout(() => {
            // hide targets
            for (let i = 0; i < trial.targets; i++) {
                obj_elems[i].className = trial.object_class;
            }
            // add effort dial
            if (trial.effort_dial) {
                configure_effort_dial();
                document.addEventListener("mousemove", update_effort_dial);
            }
            // mark animation start time
            start_time = performance.now();
            // start animation
            console.log("playing animation");
            tl.play();
        }, trial.premotion_dur);




        // called by clicking the next button
        const end_trial = () => {
            // TODO: save selection timings
            var trial_data = {
                selected_objects: selected,
                effort_dial_responses: effort_dial,
            };
            display_element.innerHTML = "";
            // console.log(trial_data);
            // end trial
            this.jsPsych.finishTrial(trial_data);
        };


        // called by `after_response`
        const allow_next = () => {
            btn_el.disabled = false;
            // btn_el.style.display = "block";
        };

        const disable_next = () => {
            btn_el.disabled = true;
            // btn_el.style.display = "none";
        };

        const configure_effort_dial = () => {
            // wave oscillator
            const real = new Float32Array(2);
            const imag = new Float32Array(2);
            real[0] = 0.05;
            imag[0] = 0.1;
            real[1] = 0.75;
            imag[1] = 0.2;
            const wave = audioCtx.createPeriodicWave(real, imag,
                                                     { disableNormalization: true });
            oscillator.setPeriodicWave(wave);
            // oscillator.frequency.value = 300.0; // defaul freq
            oscillator.connect(gain).connect(audioCtx.destination);
            // Gain settings to prevent clicking
            gain.gain.setValueAtTime(0.0, audioCtx.currentTime);
            gain.gain.setTargetAtTime(0.5, audioCtx.currentTime + 0.02, 0.01);
            const stopTime = audioCtx.currentTime + (tot_dur / 1000.0);
            gain.gain.setTargetAtTime(0, stopTime - 0.100, .025);
            oscillator.start();
        };

        // const update_mouse_pos = (e: MouseEvent) => {
        //     mouse_y = e.pageY;
        // };
        //
        const update_effort_dial = (e: MouseEvent) => {
            const dial_value: number = (e.pageX / screen_width).clamp(0.0, 1.0)
            const freq: number = dial_value * 400.0 + 200.00
            const dt = performance.now() - start_time;
            oscillator.frequency.value = freq;
            const data = [dt, dial_value];
            effort_dial.push(data);
        };
    }

}

/**
 * Returns a number whose value is limited to the given range.
 *
 * Example: limit the output of this computation to between 0 and 255
 * (x * 255).clamp(0, 255)
 *
 * Borrowed from: https://stackoverflow.com/a/11409944
 *
 * @param {Number} min The lower boundary of the output range
 * @param {Number} max The upper boundary of the output range
 * @returns A number in the range [min, max]
 * @type Number
 */
Number.prototype.clamp = function(min, max) {
    return Math.min(Math.max(this, min), max);
};

export default MOTPlugin;
