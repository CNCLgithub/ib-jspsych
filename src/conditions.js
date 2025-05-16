import protobuf from "protobufjs";

/*
  GLOBAL VARIABLES
*/
const SERVER_PATH = "78.141.233.16";
const SERVER_PORT = "3001";
const SERVER_URL = `http://${SERVER_PATH}:${SERVER_PORT}`;
const LOCK_TIMEOUT = 10 * 1000; // in ms

/*
  DATASET FORMAT
*/
const protoSchema = `

syntax = "proto3";

message Dot {
  float x = 1;
  float y = 2;
}

message Gorilla {
  float frame = 1;
  float parent = 2;
  float speedx = 3;
  float speedy = 4;
}

message Probe {
  uint32 frame = 1;
  uint32 obj = 2;
}

message Step {
  repeated Dot dots = 1;
}

message Trial {
  repeated Step steps = 1;
  optional Gorilla gorilla = 2;
  repeated Probe probes = 3;
  optional uint32 disappear = 4;
}

message Dataset {
  repeated Trial trials = 1;
}
`;

/**
 * Function to load and parse the Protobuf binary file
 */
export function parseDataset(data, buffer) {
  try {
    // Load the Protobuf schema
    const root = protobuf.parse(protoSchema).root;
    const Dataset = root.lookupType("Dataset");

    // Fetch the binary file
    // const response = fetch(filename, { method: 'GET' });
    if (!data.ok) {
      throw new Error(
        `HTTP error ${data.status}: ${data.statusText || "Unknown error"}`,
      );
    }

    // Read the binary data
    if (buffer.byteLength === 0) {
      throw new Error("Fetched file is empty");
    }

    // Decode the binary data
    const uint8Array = new Uint8Array(buffer);
    const message = Dataset.decode(uint8Array);
    return message;
  } catch (error) {
    console.error("Error loading dots:", error);
    throw error;
  }
}

/*
  BALANCING LOGIC
*/

async function unlockBatchSession(id) {
  // check if user matches id
  if (!jatos.batchSession.test(`/user`, id)) {
    console.error(`Somehow ${id} attempted to usurp active user`);
  }
  await jatos.batchSession
             .add('/user', '')
             .then(console.log(`Cleared ${id} as active user.`))
             .fail((error) => {
               console.error(`Could not clear user ${id}, `, error);
               setTimeout(() => unlockBatchSession(id), 1000);
             });
  await jatos.batchSession
             .add('/locked', false)
             .then(console.log(`Removed lock from ${id}.`))
             .fail((error) => {
               console.error('Could not unlock Batch Session: ', error);
               setTimeout(() => unlockBatchSession(id), 1000);
             });
}

async function lockBatchSession(id) {
  await jatos.batchSession
             .add('/locked', true)
             .then(console.log(`Set lock for ${id}.`))
             .fail((error) => {
               console.error(`Could not lock Batch Session for ${id}: `, error);
               checkLock(id);
               setTimeout(() => lockBatchSession(id), 1000);
             });
  await jatos.batchSession
             .add('/user', id)
             .then(console.log(`Set active user: ${id}.`))
             .fail((error) => {
               console.error(`Could not set active user ${id}: `, error);
               checkLock(id);
               setTimeout(() => lockBatchSession(id), 1000);
             });
}

async function checkLock(id) {
  // check if user is still active
  const current = jatos.batchSession.find('/user');
  if (current !== '' && !jatos.batchSession.defined(`/assigned/${current}`)) {
    console.error(`Previous user (${current}) no longer in session`);
    await unlockBatchSession(current);
  }
  const locked = jatos.batchSession.find('/locked');
  if (current === '' && locked) {
    console.error('Active user not set, but found lock in place. Attempting to clear...')
    await jatos.batchSession
               .add('/locked', false)
               .then(() => {
                 checkLock(id);
               })
               .fail((error) => {
                 console.error('Could not unjam Batch Session: ', error);
                 setTimeout(() => checkLock(id), 1000);
               });
  }
  if (current === id) {
    console.error(`Somehow ${id} is checking lock after active user`);
  } else if (locked) {
    console.log(`Batch session in use by ${current}, waiting...`);
    setTimeout(() => checkLock(id), 1000);
  }
}

async function withTimeout(procedure, timeoutMs) {
    const timeout = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Operation timed out')), timeoutMs);
    });
    return Promise.race([procedure(), timeout]);
}
async function unsafeAssignCond(prolific_pid, ncond) {
  // Already assigned
  if (jatos.batchSession.defined(`/assigned/${prolific_pid}`)) {
    const assignment = jatos.batchSession
      .find(`/assigned/${prolific_pid}`)
      .fail(() => {
        console.error(`Found record but could not read ${prolific_pid}`);
        unsafeAssignCond(prolific_pid, ncond);
      });
    return assignment;
  }

  console.log(
    `No candidates assigned to ${prolific_pid}; Sampling assignment...`,
  );
  // Find conditions that are not "full"
  const completed = jatos.batchSession.find("/completed");
  const pending = jatos.batchSession.find("/pending");
  // console.log("Completed ", completed);
  // console.log("Pending ", pending);
  let minCount = Math.min(...completed);
  const eligibleConditions = completed.flatMap((c, i) =>
    c === minCount ? i : [],
  );
  // console.log("Eligible conditions ", eligibleConditions);
  const eligiblePending = eligibleConditions
    .map(i => pending[i]);
  // console.log("Eligible pending ", eligiblePending);
  const minPending = Math.min(...eligiblePending);
  const candidates = eligiblePending.flatMap((c, i) =>
    c === minPending ? i : [],
  );
  // console.log("Candidates ", candidates);
  const candidateIdx =
    candidates[Math.floor(Math.random() * candidates.length)];
  const candidateCondition = eligibleConditions[candidateIdx];
  console.log(`Selected condition: ${candidateCondition}`);
  await jatos.batchSession
    .replace(`/pending/${candidateCondition}`,
             pending[candidateCondition] + 1)
    .then(() => jatos.batchSession
          .add(`/assigned/${prolific_pid}`, candidateCondition)
    )
    .fail(() => {
      console.error(
        `Could not assign ${prolific_pid} to ${candidateCondition}`
      );
      unsafeAssignCond(prolific_pid, ncond);
    });
  return candidateCondition;
}

async function unsafeConfirmCondition(prolific_pid, cond_idx) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, doing nothing.");
    return;
  }
  // No longer in database
  if (!jatos.batchSession.defined(`/assigned/${prolific_pid}`)) {
    console.error(`Assignment for ${prolific_pid} not found!`);
  }
  console.log(`Attempting to confirm ${prolific_pid} -> ${cond_idx}`);
  const count = jatos.batchSession.find(`/completed/${cond_idx}`);
  const pcount = jatos.batchSession.find(`/pending/${cond_idx}`);
  await jatos.batchSession
             .replace(`/completed/${cond_idx}`, count + 1)
             .then(() => {
               console.log(
                 `Updated completed record for ${prolific_pid}`
               );
             })
             .fail(() => {
               console.error(
                 `Cound not update completed record for ${prolific_pid}`
               );
             });
  await jatos.batchSession
             .replace(`/pending/${cond_idx}`,
                      pcount - 1)
             .then(() => {
               console.log(
                 `Updated pending record for ${prolific_pid}`
               );
             })
             .fail(() => {
               console.error(
                 `Cound not update pending record for ${prolific_pid}`
               );
             });

  await jatos.batchSession.remove(`/assigned/${prolific_pid}`)
             .then(() => {
               console.log(
                 `Removed assignment record for ${prolific_pid}`
               );
             })
             .fail(() => {
               console.error(
                 `Cound not clear record for ${prolific_pid}`
               );
             });
}

/*
  BALANCING API
*/

export async function initConditionCounts(ncond = 24) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, nothing to initialize...");
    return Math.floor(Math.random() * ncond);
  }
  // Check if 'conditions' are not already in the batch session
  if (!jatos.batchSession.defined("/locked")) {
    console.log(
      "No exisiting Batch data found, initializing condition counts...",
    );
    const conditionCounts = Array(ncond).fill(0);
    const batchData = {
      completed : Array(ncond).fill(0),
      pending   : Array(ncond).fill(0),
      assigned  : {},
      locked : false,
      user : '',
    };
    // Put the conditions in the batch session
    await jatos.batchSession
      .setAll(batchData)
      .then(() => {
        console.log("Initialized Batch Data successfully");
      })
      .fail(() => {
        console.error("Cound not init conditions");
        initConditionCounts(ncond);
      });
  }
}

export async function assignCondition(prolific_pid, ncond = 24) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, sampling random condition");
    return Math.floor(Math.random() * ncond);
  }
  console.log("In JATOS, checking lock...");
  await checkLock(prolific_pid); // loops until lock is free
  console.log("Open, locking for current session...");
  await lockBatchSession(prolific_pid);
  console.log("Locked. Generating assignment...");
  const assignment = await withTimeout(
    () => unsafeAssignCond(prolific_pid, ncond),
    LOCK_TIMEOUT
  ).catch(error => {
    console.error("Could not retreive assignment: ", error);
    return Math.floor(Math.random() * ncond);
  });
  console.log("Assignment completed. Unlocking...");
  await unlockBatchSession(prolific_pid);
  console.log(`...unlocked. Done with ${prolific_pid}.`);
  return assignment;
}

export async function confirmCondition(prolific_pid, cond_idx) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, doing nothing.");
    return;
  }
  console.log("In JATOS, checking lock...");
  await checkLock(prolific_pid); // loops until lock is free
  console.log("Open, locking for current session...");
  await lockBatchSession(prolific_pid);
  console.log("Locked. Confirming assignment...");
  await withTimeout(
    () => unsafeConfirmCondition(prolific_pid, cond_idx),
    LOCK_TIMEOUT
  ).catch(error => {
    console.error("Could not confirm assignment: ", error);
  });
  console.log("Confirmation completed. Unlocking...");
  await unlockBatchSession(prolific_pid);
  console.log(`...unlocked. Done with ${prolific_pid}.`);
}
