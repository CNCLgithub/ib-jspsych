import protobuf from "protobufjs";

/*
  GLOBAL VARIABLES
*/
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

async function withTimeout(procedure, timeoutMs) {
  const timeout = new Promise((_, reject) => {
    setTimeout(() => reject(new Error("Operation timed out")), timeoutMs);
  });
  return Promise.race([procedure(), timeout]);
}

function tallyCounts(n) {
  const completed = jatos.batchSession.find("/completed");
  const pending = jatos.batchSession.find("/pending");
  const ccounts = Array(n).fill(0);
  const pcounts = Array(n).fill(0);
  Object.entries(completed).forEach(([key, value]) => {
    ccounts[value]++;
  });
  Object.entries(pending).forEach(([key, value]) => {
    pcounts[value]++;
  });
  return [ccounts, pcounts];
}

async function unsafeAssignCond(prolific_pid, ncond) {
  // Already assigned
  if (jatos.batchSession.defined(`/pending/${prolific_pid}`)) {
    const assignment = jatos.batchSession
      .find(`/pending/${prolific_pid}`)
      .then(() => {
        console.log(`Found pending for ${prolific_pid}`);
      })
      .fail((error) => {
        console.error(`Could not retrieve pending for ${prolific_pid}:`,
                      error, '\nretrying...');
        unsafeAssignCond(prolific_pid, ncond);
      });
    return assignment;
  }

  console.log(`Generating new assignment for ${prolific_pid} ...`);
  // Find conditions that are not "full"
  const [completed, pending] = tallyCounts(ncond);
  console.log("Completed ", completed);
  console.log("Pending ", pending);
  let minCount = Math.min(...completed);
  const eligibleConditions = completed.flatMap((c, i) =>
    c === minCount ? i : [],
  );
  console.log("Eligible conditions ", eligibleConditions);
  const eligiblePending = eligibleConditions.map((i) => pending[i]);
  console.log("Eligible pending ", eligiblePending);
  const minPending = Math.min(...eligiblePending);
  const candidates = eligiblePending.flatMap((c, i) =>
    c === minPending ? i : [],
  );
  console.log("Candidates ", candidates);
  const candidateIdx =
    candidates[Math.floor(Math.random() * candidates.length)];
  const candidateCondition = eligibleConditions[candidateIdx];
  console.log(`Selected condition: ${candidateCondition}`);
  await jatos.batchSession
    .add(`/pending/${prolific_pid}`, candidateCondition)
    .then(() => {
      console.log(
        `Successfully assigned ${prolific_pid} to ${candidateCondition}`,
      );
    })
    .fail((error) => {
      console.error(
        `Failed to assign ${prolific_pid} to ${candidateCondition}:\n`,
        error, `/n...retrying`,
      );
      unsafeAssignCond(prolific_pid, ncond);
    });
  return candidateCondition;
}

async function unsafeConfirmCondition(prolific_pid) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, doing nothing.");
    return;
  }
  // No longer in database
  if (!jatos.batchSession.defined(`/pending/${prolific_pid}`)) {
    console.error(`Pending record for ${prolific_pid} not found!`);
  }
  if (jatos.batchSession.defined(`/completed/${prolific_pid}`)) {
    console.error(`${prolific_pid} already marked as completed! Doing nothing`);
    return;
  }
  await jatos.batchSession
    .move(`/pending/${prolific_pid}`, `/completed/${prolific_pid}`)
    .then(() => {
      console.log(`Successfully confirmed ${prolific_pid} as completed`);
    })
    .fail((error) => {
      console.error(`Failed to confirm ${prolific_pid} as completed\n`,
                    error,
                    '\n...retrying');
      unsafeConfirmCondition(prolific_pid);
    });
}

/*
  BALANCING API
*/

// export async function initBatchSession() {
//   if (typeof jatos === "undefined") {
//     console.log("Not in JATOS, nothing to initialize...");
//     return;
//   } else {
//     // random slow down to prevent race conditions
//     await new Promise(r => setTimeout(r, 200 + 1000 * Math.random()));
//   }
//   // Check if 'conditions' are not already in the batch session
//   if (jatos.batchSession.defined("/completed")) {
//     console.log("Found exisisting Batch session");
//     return;
//   }
//   console.log(
//     "No exisiting Batch session found, initializing...",
//   );
//   const batchData = {
//     completed: {},
//     pending: {},
//   };
//   // Put the conditions in the batch session
//   await jatos.batchSession
//              .setAll(batchData)
//              .then(() => {
//                console.log(
//                  "Successfully initialized Batch session"
//                );
//              })
//              .fail((error) => {
//                console.error(
//                  "Failed to initialized Batch session\n",
//                  error,
//                  "\n..retrying"
//                );
//                initBatchSession();
//              });
// }

export async function assignCondition(prolific_pid, session_id, ncond) {
  try {
    const response = await fetch(`http://localhost:3001/assign-condition?prolific_pid=${prolific_pid}&session_id=${session_id}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();
    return data.condition;
  } catch (error) {
    console.error('Error fetching candidate condition:', error);
    // Fallback: Random assignment
    return Math.floor(Math.random() * ncond);
  }
}

export async function confirmCondition(prolific_pid, session_id) {
  try {
    await fetch('http://localhost:3001/confirm-condition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prolific_pid, session_id })
    });
  } catch (error) {
    console.error('Error confirming condition:', error);
  }
}
