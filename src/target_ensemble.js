/**
 * @title Event counting
 * @description Count the number of times objects bounce
 * @version 0.1.0
 *
 * @assets assets/
 */

// You can import stylesheets (.scss or .css).
import "../styles/main.scss";
// Plugins
import PreloadPlugin from "@jspsych/plugin-preload";
import FullscreenPlugin from "@jspsych/plugin-fullscreen";
import SurveyTextPlugin from "@jspsych/plugin-survey-text";
import SurveyMultiChoicePlugin from "@jspsych/plugin-survey-multi-choice";
import ExternalHtmlPlugin from "@jspsych/plugin-external-html";
// import VirtualChinrestPlugin from '@jspsych/plugin-virtual-chinrest';
import InstructionsPlugin from "@jspsych/plugin-instructions";
import HTMLButtonResponsePlugin from "@jspsych/plugin-html-button-response";
import HTMLSliderResponsePlugin from "@jspsych/plugin-html-slider-response";
import IBPlugin from "./plugins/ib.ts";
import { initJsPsych } from "jspsych";
import {
  parseDataset,
  assignCondition,
  confirmCondition,
  initConditionCounts,
} from "./conditions.js";
// Prolific variables
const PROLIFIC_URL = "https:app.prolific.com/submissions/complete?cc=C1EB8IGX";

// Define global experiment variables
const OBJ_RADIUS = 20;
const nscenes = 6;
const scenes = [...Array(nscenes).keys()];
const parents = ["ensemble", "lone"];
const CONDITIONS = scenes.flatMap((scene) =>
  parents.map((parent) => ({
      scene: scene,
      parent: parent,
  })),
);
const NCOND = CONDITIONS.length;
const NTRIALS = 5;
const MAXBOUNCES = 10;
const COUNT_LABELS = [...Array(MAXBOUNCES + 1).keys()].map((x) => `${x}`);
// const TIME_PER_TRIAL = dataset[0].positions.length / 24;
var EXP_DURATION = 5; //  in minutes
const MOT_WIDTH = 720; // pixels
const MOT_HEIGHT = 480; // pixels
// const STIM_DEG = 10;
// const PIXELS_ER_UNIT = MOT_DIM / STIM_DEG;
var CHINREST_SCALE = 1.0; // to adjust pixel dimensions
// Debug Variables
const SKIP_INSTRUCTIONS = false;
// const SKIP_INSTRUCTIONS = true;
// const SKIP_PROLIFIC_ID = true;

function gen_trial(
  jsPsych,
  trial_id,
  scene,
  measure_count = true,
  show_gorilla = false,
  parent = "ensemble",
  appearance = "ib-target",
) {
  const display_width = MOT_WIDTH * CHINREST_SCALE;
  const display_height = MOT_HEIGHT * CHINREST_SCALE;
  let parent_idx = -1;
  if (show_gorilla) {
    // ENSEMBLE | LONE TARGET
    parent_idx = parent == "ensemble" ? 0 : 3;
  }
  const tracking = {
    type: IBPlugin,
    scene: scene,
    targets: 4,
    object_radius: OBJ_RADIUS,
    distractor_class: "ib-distractor",
    target_class: "ib-target",
    parent: parent_idx,
    gorilla_class: "ib-target",
    probe_class: "ib-probe",
    display_width: display_width,
    display_height: display_height,
    flip_height: false,
    flip_width: false,
    flip_height: jsPsych.randomization.sampleBernoulli(0.5),
    flip_width: jsPsych.randomization.sampleBernoulli(0.5),
    world_scale: 720.0, // legacy datasets are +- 400 units
    premotion_dur: 2000.0,
    show_prompt: measure_count,
    // step_dur: 100.0,
  };

  const sub_tl = [tracking];

  if (measure_count) {
    sub_tl.push({
      type: HTMLSliderResponsePlugin,
      stimulus:
        `<div style="width:${display_width}px;">` +
        `<p>How many times did the targets bounce?</p></div>`,
      require_movement: true,
      labels: COUNT_LABELS,
      min: 0,
      max: MAXBOUNCES,
      slider_start: 0,
    });
  }

  if (parent_idx >= 0) {
    sub_tl.push({
      type: HTMLButtonResponsePlugin,
      choices: ["Yes", "No"],
      stimulus:
        `<div style="width:${display_width}px;">` +
        `<p>Did you notice anything unusual or out of the ` +
        ` ordinary while performing the last trial?</p></div>`,
    });
    const gorilla_desc = {
      type: SurveyTextPlugin,
      questions: [
        {
          prompt:
            `<div style="width:${display_width}px;">` +
            `<p>Please, describe what you noticed.</p></div>`,
          required: true,
        },
      ],
    };
    sub_tl.push({
      timeline: [gorilla_desc],
      conditional_function: function () {
        // get the data from the previous trial,
        // and check which key was pressed
        var data = jsPsych.data.get().last(1).values()[0];
        // clicked yes
        return data.response == 0;
      },
    });
  }

  const tl = {
    timeline: sub_tl,
    data: {
      trial_id: trial_id,
      measure_count: measure_count,
      appearance: appearance,
      parent: parent,
    },
  };
  return tl;
}

function trialsFromCondition(jsPsych, dataset, condition) {
  let trials = [];
  for (let i = 1; i < NTRIALS; i++) {
    const tidx = (condition.scene + i) % nscenes;
    trials.push(gen_trial(jsPsych, tidx + 1, dataset.trials[tidx]));
  }
  trials = jsPsych.randomization.repeat(trials, 1);
  trials.push(
    gen_trial(
      jsPsych,
      condition.scene + 1,
      dataset.trials[condition.scene],
      true,
      true,
      condition.parent,
    ),
  );
  return trials;
}

/**
 * This function will be executed by jsPsych Builder and is expected to run the jsPsych experiment
 *
 * @type {import("jspsych-builder").RunFunction}
 */
export async function run({
  assetPaths,
  input = {},
  environment,
  title,
  version,
}) {
  let prolific_id = "";
  let cond_idx = -1;

  const jsPsych = initJsPsych({
    show_progress_bar: true,
    on_finish: () => {
      if (typeof jatos !== "undefined") {
        // in jatos environment
        confirmCondition(prolific_id, cond_idx);
        jatos.endStudyAndRedirect(PROLIFIC_URL, jsPsych.data.get().json());
      } else {
        return jsPsych;
      }
    },
  });

  if (typeof jatos !== "undefined") {
    await initConditionCounts(CONDITIONS.length);
    prolific_id = jatos.urlQueryParameters.PROLIFIC_PID ||
      `UNKNOWN_${jsPsych.randomization.randomID()}`;
  } else {
    prolific_id = `UNKNOWN_${jsPsych.randomization.randomID()}`;
  }


  console.log(prolific_id);

  cond_idx = await assignCondition(prolific_id, CONDITIONS.length);
  const condition = CONDITIONS[cond_idx];
  const timeline = [];
  const DATASETRAW = await fetch("assets/dataset.bin", { method: "GET" });
  const DATASETBUFFER = await DATASETRAW.arrayBuffer();
  const DATASET = parseDataset(DATASETRAW, DATASETBUFFER);

  const EXAMPLESRAW = await fetch("assets/examples.bin", { method: "GET" });
  const EXAMPLESBUFFER = await EXAMPLESRAW.arrayBuffer();
  const EXAMPLES = parseDataset(EXAMPLESRAW, EXAMPLESBUFFER);

  // REVIEW: add more examples?
  const EXAMPLE1 = EXAMPLES.trials[0];
  const EXAMPLE2 = EXAMPLES.trials[1];
  const EXAMPLE3 = EXAMPLES.trials[2];
  const N_TRIALS = DATASET.trials.length;

  // Consent
  timeline.push({
    type: ExternalHtmlPlugin,
    url: "assets/consent.html",
    cont_btn: "start",
    check_fn: function () {
      if (document.getElementById("consent_checkbox").checked) {
        return true;
      } else {
        alert("You must tick the checkbox to continue with the study.");
      }
    },
  });

  // Preload assets
  timeline.push({
    type: PreloadPlugin,
    images: assetPaths.images,
    audio: assetPaths.audio,
    video: assetPaths.video,
  });

  // Welcome screen
  timeline.push({
    type: InstructionsPlugin,
    pages: [
      `<h1>Hi, welcome to our study!</h1><br><br> ` +
        `Please take a moment to adjust your seating so that you can comfortably watch the monitor and use the keyboard/mouse.<br> ` +
        `Feel free to dim the lights as well.  ` +
        `Close the door or do whatever is necessary to minimize disturbance during the experiment. <br> ` +
        `Please also take a moment to silence your phone so that you are not interrupted by any messages mid-experiment. ` +
        `<br><br> ` +
        `Click <b>Next</b> when you are ready to calibrate your display. `,
    ],
    show_clickable_nav: true,
    allow_backward: false,
    data: {
      type: "welcome",
    },
  });

  // Switch to fullscreen
  timeline.push({
    type: FullscreenPlugin,
    fullscreen_mode: true,
  });

  // Virtual chinrest
  // timeline.push({
  //   type: VirtualChinrestPlugin,
  //   blindspot_reps: 3,
  //   resize_units: "deg",
  //   pixels_per_unit: PIXELS_PER_UNIT,
  //   on_finish: function(data) {
  //     CHINREST_SCALE = data.scale_factor;
  //   },
  // });

  const instruct_tl = [];
  instruct_tl.push({
    type: InstructionsPlugin,
    pages: [
      `The study is designed to be <i>challenging</i>. <br> ` +
        ` Sometimes, you'll be certain about what you saw. <br>` +
        `Other times, you won't be -- and this is okay!<br>` +
        `Just give your best guess each time. <br><br>` +
        `Click <b>Next</b> to continue.`,

      `We know it is also difficult to stay focused for so long, especially when you are doing the same ` +
        `thing over and over.<br> But remember, the experiment will be all over in less than ${EXP_DURATION} minutes.` +
        ` There are <strong>${N_TRIALS} trials</strong> in this study. <br>` +
        `Please do your best to remain focused! ` +
        ` Your responses will only be useful to us if you remain focused. <br><br>` +
        `Click <b>Next</b> to continue.`,

      "In this task, you will observe a series of objects move on the screen.<br>" +
        "Click <b>Next</b> to see an example of a dynamic scene.",
    ],
    show_clickable_nav: true,
    show_page_number: true,
    page_label: "<b>Instructions</b>",
    allow_backward: false,
  });

  instruct_tl.push(gen_trial(jsPsych, 0, EXAMPLE1, false));

  instruct_tl.push({
    type: InstructionsPlugin,
    pages: [
      "Your task is to count the number of times the light objects bounce against the walls of the display.<br>" +
        `At the end of each instance of the task, you will respond using a slider.<br>` +
        `If you lost count of the number of bounces, just make your best guess.<br>` +
        "Click <b>Next</b> to give it a try.",
    ],
    show_clickable_nav: true,
    show_page_number: true,
    page_label: "<b>Instructions</b>",
    allow_backward: false,
  });

  instruct_tl.push(gen_trial(jsPsych, 0, EXAMPLE1));

  instruct_tl.push({
    type: InstructionsPlugin,
    pages: [
      "<span style='overflow-wrap:anywhere'>The task is designed to be difficult. <br> " +
        "It's ok if you are unsure about your responses, they will be helpfull to us either way.<br>" +
        "Click <b>Next</b> to take a short comprehension quiz.",
    ],
    show_clickable_nav: true,
    show_page_number: true,
    page_label: "<b>Instructions</b>",
    allow_backward: false,
  });

  // comprehension check
  const comp_check = {
    type: SurveyMultiChoicePlugin,
    preamble:
      "<h2>Comprehension Check</h2> " +
      "<p> Before beginning the experiment, you must answer a few simple questions to ensure that the instructions are clear." +
      "<br> If you do not answer all questions correctly, you will be returned to the start of the instructions.</p>",
    questions: [
      {
        prompt: "Which of the following is <b>TRUE</b>",
        name: "check1",
        options: [
          "A) Before motion, you have to click on all of the light objects",
          "B) The main task is to count the number of bounces from light objects",
          "C) Only respond if you are 100% sure about the answer",
        ],
        required: true,
      },
      {
        prompt: " Which of the following statements is <b>FALSE</b>:",
        name: "check2",
        options: [
          "A) You will use a slider to report the number of bounces",
          "B) To move on to the next trial, you must move the slider",
          "C) You can move objects with your mouse",
        ],
        required: true,
      },
    ],
    randomize_question_order: false,
    on_finish: function (data) {
      const q1 = data.response.check1[0];
      const q2 = data.response.check2[0];
      // both comp checks must pass
      data.correct = q1 == "B" && q2 == "C";
    },
    data: {
      type: "comp_quiz",
    },
  };

  // feedback
  const comp_feedback = {
    type: HTMLButtonResponsePlugin,
    stimulus: () => {
      var last_correct_resp = jsPsych.data
        .getLastTrialData()
        .values()[0].correct;
      var msg;
      if (last_correct_resp) {
        msg =
          "<h2><span style='color:green'>You passed the comprehension check!</span>" +
          "<br>When you're ready, please click <b>Next</b> to begin the study. </h2>";
      } else {
        msg =
          "<h2><span style='color:red'>You failed to respond <b>correctly</b> to all" +
          " parts of the comprehension check.</span>" +
          "<br>Please click <b>Next</b> to revisit the instructions.</h2>";
      }
      return msg;
    },
    choices: ["Next"],
    data: {
      // add any additional data that needs to be recorded here
      type: "comp_feedback",
    },
  };

  // `comp_loop`: if answers are incorrect, `comp_check` will be repeated until answers are correct responses
  const comp_loop = {
    timeline: [...instruct_tl, comp_check, comp_feedback],
    loop_function: function (data) {
      // return false if comprehension passes to break loop
      // HACK: changing `timeline` will break this
      const vals = data.values();
      const quiz = vals[vals.length - 2];
      return !quiz.correct;
    },
  };

  // add comprehension loop
  if (!SKIP_INSTRUCTIONS) {
    timeline.push(comp_loop);
  }

  // add exp trials
  timeline.push(...trialsFromCondition(jsPsych, DATASET, condition));

  // debriefing
  timeline.push({
    type: SurveyTextPlugin,
    preamble:
      `<h2><b>Thank you for helping us with our study! ` +
      `This study was designed to be difficult and we value your responses. </b></h2><br><br> ` +
      `Please fill out the (optional) survey below and click <b>Done</b> to complete the experiment. <br> `,
    questions: [
      {
        prompt:
          "Did you find yourself using any strategies while performing the task?",
        name: "Strategy",
        rows: 5,
        placeholder: "None",
      },

      {
        prompt: "Are there any additional comments you'd like to add? ",
        name: "General",
        rows: 5,
        placeholder: "None",
      },
    ],
    button_label: "Done",
  });

  await jsPsych.run(timeline);

  // Return the jsPsych instance so jsPsych Builder can access the experiment results (remove this
  // if you handle results yourself, be it here or in `on_finish()`)
  return jsPsych;
}
