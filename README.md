# Sustained Inattentional Blindness

This repo contains a jsPsych implementation of Steve Mosts' Sustained Inattentional Blindness paradigm.
There are several additional extensions such as ...

The main logic is defined under `src/*.js` and the plugin `plugin/mot.ts`.

>NOTE: This is a work in progress! API subject to change

## Setup

Using the [jspsych builder](https://github.com/bjoluc/jspsych-builder) tool, all that's needed to get running is to run

1. `npm install` to install all node dependencies
2. `npm start` to build and run a local server package the experiment as a static website for [JATOS](https://www.jatos.org/)

<!-- TODO: add wget script to download stimuli into `assets` -->

## Deployment

Two options

1. `npm run jatos` to package the experiment as a static website for [JATOS](https://www.jatos.org/)

or 

2. `npm run build` to package the experiment as a static website for independent management. 

> Note that option 2 would require modification in order to store subject responses
