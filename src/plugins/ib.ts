import { JsPsych, JsPsychPlugin, ParameterType, TrialType } from "jspsych";
import {
    createTimeline,
    engine,
    animate,
} from 'animejs';

engine.defaults.autoplay = false;

const LOCERROR = 'LOCERROR';
const PROBE = 'PROBE';
const NOTASK = 'NOTASK';

export type ValidTask = 'NOTASK' | 'PROBE' | 'LOCERROR';

const info = <const>{
    name: "IB",
    parameters: {
        scene: {
            // BOOL, STRING, INT, FLOAT, FUNCTION, KEY, KEYS, SELECT, HTML_STRING,
            // IMAGE, AUDIO, VIDEO, OBJECT, COMPLEX
            type: ParameterType.OBJECT,
            description: "A protobuf object describing object tractories, probe timings, etc.",
        },
        targets: {
            type: ParameterType.INT,
            description: "The first N objects in `scene` are denoted as targets."
        },
        distractor_class: {
            type: ParameterType.STRING,
            description: "The css class describing distractor appearance.",
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
            default: "NOTASK",
            description: "NOTASK | PROBE | LOCERROR",
        },
        world_scale: {
            type: ParameterType.FLOAT,
            default: 1.0,
            description: "Scaling factor for object trajectories.",
        },
    },
};

type Info = typeof info;

type LocResponse = {
    rt: number;
    clickX: number;
    clickY: number;
};

/**
 * **IB**
 *
 * Track objects with your mind!
 *
 * @author Mario Belledonne
 * @see {@link https://DOCUMENTATION_URL DOCUMENTATION LINK TEXT}
 */
class IBPlugin implements JsPsychPlugin<Info> {
    static info = info;

    constructor(private jsPsych: JsPsych) { }

    trial(display_element: HTMLElement, trial: TrialType<Info>) {
        /**
         * SETUP
         */
        display_element.innerHTML = '';
        // VARIABLE DECLARATIONS
        const scene = trial.scene;
        const state = scene.steps;
        const n_objects = state[0].dots.length;
        const obj_elems = Array<HTMLElement>(n_objects);
        let task_prompt: HTMLElement;
        let start_time: number = 0.0;
        const tot_dur = trial.step_dur * state.length;
        // pixels per world unit
        const world_to_display = trial.display_width / trial.world_scale;
        // assuming objects are 40 units -> how many pixels
        const obj_dim = 40.0 * world_to_display; // REVIEW
        const probe_dim = 5.0 * world_to_display; // REVIEW
        const screen_width = document.getElementsByTagName('body')[0].offsetWidth;


        let location: LocResponse;
        let probe_responses: Array<number> = [];

        // probe element
        const probe_elem = document.createElement("span");
        probe_elem.id = "probe";
        probe_elem.className = trial.probe_class;
        display_element.appendChild(probe_elem);

        // ELEMENTS
        let ib_el = document.createElement("div");
        ib_el.className = "ib-div";
        ib_el.style = `width:${trial.display_width}px;height:${trial.display_height}px`;
        display_element.appendChild(ib_el);
        // if the task==LOCERROR, gets rewritten later
        let animate_locresponse = () => {};

        // initialize animation timeline
        const tl = createTimeline({
            defaults: {
                ease: 'linear',
            },
            autoplay: false,
            onBegin : () => {
                // mark animation start time
                start_time = performance.now();
            },
            // add prompt at end of animation
            onComplete : () => {
                if (trial.task == LOCERROR) {
                    animate_locresponse();
                } else {
                    // NOTASK and PROBES just ends the trial immediatly
                    end_trial();
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
            const css_cls = (i < trial.targets) ?
                trial.target_class : trial.distractor_class
            const obj_el = document.createElement("span");
            obj_el.className = css_cls;
            // initial positions of objects
            const dot = state[0].dots[i];
            const [x, y] = t_pos([dot.x, dot.y]);
            obj_el.setAttribute(
                "style",
                `width:${obj_dim}px;height:${obj_dim}px;` +
                    `transform:translateX(${x}px) translateY(${y}px);`
            );
            obj_el.id = `obj_${i}`;
            // store info
            ib_el.appendChild(obj_el);
            obj_elems[i] = obj_el;
        }

        /**
         * ANIMATIONS
         */

        // motion phase
        for (let i = 0; i < n_objects; i++) {
            const positions = state.map((step) => {
                const obj = step.dots[i];
                return (t_pos([obj.x, obj.y]));
            });
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

        // subtask animations
        // probes
        if (trial.task == PROBE) {
            if (!scene.hasOwnProperty('probes')) {
                throw new TypeError('Trial does not have `probes` field');
            }
            const probes = scene.probes;
            // animation for each probe
            const probe_anim = (frame: number, obj_id: number) => {
                const positions = state
                    .slice(frame, frame + trial.probe_steps)
                    .map(step => {
                        const obj = step.dots[obj_id];
                        return (t_pos([obj.x, obj.y], probe_dim));
                    });
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
            for (let probe_frame of probes) {
                const [frame, obj_id] = probe_frame;
                probe_anim(frame, obj_id);
            }
        }
        // loc
        if (trial.task == LOCERROR) {
            if (!scene.hasOwnProperty('disappear')) {
                throw new TypeError('Trial does not have `disappear` field');
            }
            animate_locresponse = () => {
                animate(obj_elems[scene.disappear - 1], {
                    opacity: 0,
                    duration: 150,
                    ease: 'out(3)',
                    autoplay: true,
                    onComplete: () => {
                        // RT from end of animation
                        task_prompt.setAttribute('style', 'color:black');
                        start_time = performance.now();
                    }
                })
            };
        }


        /**
         * RESPONSE LOGIC
         */

        const after_loc_response = (click:MouseEvent) => {
            if (tl.completed) {
                const rt = performance.now() - start_time;
                const bbox = ib_el.getBoundingClientRect();
                location = {
                    rt: rt,
                    clickX: (click.clientX - bbox.left) / bbox.width,
                    clickY: (click.clientY - bbox.top) / bbox.height,
                };
                end_trial();
            }
        };
        const after_probe_response = (kbe: KeyboardEvent) => {
            if (!tl.completed &&
                this.jsPsych.pluginAPI.compareKeys(kbe.key, ' ')) {
                const rt = performance.now() - start_time;
                probe_responses.push(rt);
                animate(ib_el, {
                    'border-color': '#ffffff',
                    loop: 3,
                    alternate: true,
                    ease: 'out(3)',
                    duration : 75,
                    autoplay: true,
                });
            }
        };

        // task prompt
        task_prompt = document.createElement("div");
        task_prompt.setAttribute('class', 'jspsych-top');
        if (trial.task == LOCERROR) {
            task_prompt.setAttribute('style', 'color:white');
            task_prompt.innerHTML =
                'Click where the missing object was';
            ib_el.addEventListener("click", after_loc_response);

        } else if (trial.task == PROBE) {
            task_prompt.setAttribute('style', 'color:black');
            task_prompt.innerHTML = 'Press SPACE when you see a probe';
            document.addEventListener('keydown', after_probe_response);
        }
        display_element.appendChild(task_prompt);

        // START ANIMATION
        this.jsPsych.pluginAPI.setTimeout(() => {tl.play()}, trial.premotion_dur);

        // end trial
        const end_trial = () => {
            if (trial.task == PROBE) {
                document.removeEventListener('keydown', after_probe_response);
            } else if (trial.task == LOCERROR) {
                ib_el.removeEventListener('click', after_loc_response);
            }
            var trial_data = {
                location : location,
                probe_responses : probe_responses,
            };
            display_element.innerHTML = "";
            this.jsPsych.finishTrial(trial_data);
        };
    }

}

export default IBPlugin;
