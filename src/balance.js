/**
 * @title Balance testing
 * @description Count the number of times objects bounce
 * @version 0.1.0
 *
 */


/*
  IMPORTS
*/

// You can import stylesheets (.scss or .css).
import "../styles/main.scss";
// Plugins
import HTMLButtonResponsePlugin from "@jspsych/plugin-html-button-response";
import IBPlugin from "./plugins/ib.ts";
import { initJsPsych } from "jspsych";
import {
  parseDataset,
  assignCondition,
  confirmCondition,
  initBatchSession,
} from "./conditions.js";


/*
  GLOBAL VARIABLES
*/

// Prolific variables
const PROLIFIC_URL = "https:app.prolific.com/submissions/complete?cc=C1EB8IGX";

// Define global experiment variables
const SWAP_APEARANCE = true; // for control experiment
const TARGET = `<span style="color:#808080;"><b>LIGHT</b></span>`;
const OBJ_RADIUS = 20; // in world units
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
    on_finish: async () => {
      if (typeof jatos !== "undefined") {
        // in jatos environment
        await confirmCondition(prolific_id);
        // const redirect = jatos.studyJsonInput.PROLIFIC_URL ||
        //       PROLIFIC_URL;
        // jatos.endStudyAndRedirect(redirect, jsPsych.data.get().json());
        jatos.endStudy(jsPsych.data.get().json());
      } else {
        return jsPsych;
      }
    },
  });
  if (typeof jatos !== "undefined") {
    await initBatchSession();
    prolific_id =
      jatos.urlQueryParameters.PROLIFIC_PID ||
      `UNKNOWN_${jsPsych.randomization.randomID()}`;
  } else {
    prolific_id = `UNKNOWN_${jsPsych.randomization.randomID()}`;
  }
  cond_idx = await assignCondition(prolific_id, CONDITIONS.length);
  const condition = CONDITIONS[cond_idx];
  const rand_rt = 1000 + Math.random() * 4000;
  const timeline = [{
    type: HTMLButtonResponsePlugin,
    stimulus: '<p style="font-size:48px; color:green;">BLUE</p>',
    choices: ['r', 'g', 'b'],
    prompt: "<p>Is the ink color (r)ed, (g)reen, or (b)lue?</p>",
    trial_duration: rand_rt,
  }];
  await jsPsych.run(timeline);
  // Return the jsPsych instance so jsPsych Builder can access the experiment results (remove this
  // if you handle results yourself, be it here or in `on_finish()`)
  return jsPsych;
}
