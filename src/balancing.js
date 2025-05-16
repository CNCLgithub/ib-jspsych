/**
 * @title Load balancing test
 * @description Count the number of times objects bounce
 * @version 0.1.0
 *
 * @assets assets/
 */

// You can import stylesheets (.scss or .css).
import "../styles/main.scss";
import callFunction from '@jspsych/plugin-call-function';
import { initJsPsych } from "jspsych";
import {
  assignCondition,
  confirmCondition,
  initConditionCounts,
} from "./conditions.js";
const NCOND = 4;
const TIMEMIN=3 * 1000;
const TIMEMAX=10 * 1000;
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
      console.log("Finished study!")
      if (typeof jatos !== "undefined") {
        // in jatos environment
        confirmCondition(prolific_id, cond_idx);
      }
      return jsPsych;
    },
  });

  if (typeof jatos !== "undefined") {
    await initConditionCounts(NCOND);
    prolific_id =
      jatos.urlQueryParameters.PROLIFIC_PID ||
      `UNKNOWN_${jsPsych.randomization.randomID()}`;
  } else {
    prolific_id = `UNKNOWN_${jsPsych.randomization.randomID()}`;
  }

  cond_idx = await assignCondition(prolific_id, NCOND);

  jsPsych.data.addProperties({
    subject: prolific_id,
    condition: cond_idx,
  });
  let timeline = [];
  timeline.push({
    type: callFunction,
    async: true,
    func: async (done) => {
      // generate a delay between 1500 and 5000 milliseconds to simulate
      // waiting for an event to finish after an unknown duration,
      // then move on with the experiment
      const rand_delay = (Math.floor(Math.random() * (TIMEMAX-TIMEMIN) + TIMEMIN));
      console.log(`Taking ${rand_delay}ms to finish`);
      jsPsych.pluginAPI.setTimeout(function() {
        // end the trial and save the delay duration to the data
        done(rand_delay.toString()+"ms");
      }, rand_delay)
    }
  });
  // jsPsych.data.addDataToLastTrial({hello : "world"});

  await jsPsych.run(timeline);
  // Return the jsPsych instance so jsPsych Builder can access the experiment results (remove this
  // if you handle results yourself, be it here or in `on_finish()`)
  // return jsPsych;
}
