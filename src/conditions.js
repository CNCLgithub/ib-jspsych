import protobuf from "protobufjs";

/*
  GLOBAL VARIABLES
*/
const LOCK_TIMEOUT = 10 * 1000; // in ms
const dbserver = "http://localhost";
// const dbserver = "http://78.141.233.16";
const port = 3001;

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

const assign_base = `${dbserver}:${port}/assign-condition`;
async function unsafeAssignCond(prolific_pid, session_id) {
  return fetch(
    `${assign_base}?prolific_pid=${prolific_pid}&session_id=${session_id}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    }
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error('Error parsing response from server', response);
    }
    const data = await response.json();
    return data.condition;
  })
    .catch((error) => {
      throw new Error(`Issue with server: ${error.message}`);
    })
}

const confirm_base = `${dbserver}:${port}/confirm-condition`;
async function unsafeConfirmCondition(prolific_pid, session_id) {
  return fetch(
    confirm_base,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prolific_pid, session_id })
    }
  ).then((response) => {
    if (!response.ok) {
      throw new Error('Error parsing response from server', response);
    }
    console.log(
      `Confirmed assignment of ${prolific_pid} to ${session_id} on server`
    );
  }).catch((error) => {
      throw new Error(`Issue with server: ${error.message}`);
  });
}

/*
  BALANCING API
*/
async function retryPromise(promiseFunc, timeoutMs) {
  const startTime = Date.now();
  let error;
  while (Date.now() - startTime < timeoutMs) {
    try {
      return await promiseFunc();
    } catch (err) {
      error = err.message;
      // Wait briefly before retrying to prevent tight loops
      await new Promise(resolve => setTimeout(resolve, 250));
    }
  }
  throw new Error(`Timeout reached (after ${timeoutMs}ms) before promise resolved: ${error}`);
}

export async function assignCondition(prolific_pid, session_id, ncond) {
  // Wait briefly before retrying to prevent tight loops
  await new Promise(resolve => setTimeout(resolve, 250 + 1000*Math.random()));
  const assignment = await retryPromise(
    async () => unsafeAssignCond(prolific_pid, session_id),
    LOCK_TIMEOUT,
  ).catch((error) => {
    console.error("Failed to generate assignment:\n ",
      error,
      "\n Falling back to random assignment.");
    return Math.floor(Math.random() * ncond);
  });
  return assignment;
}

export async function confirmCondition(prolific_pid, session_id) {
  // Wait briefly before retrying to prevent tight loops
  await new Promise(resolve => setTimeout(resolve, 250 + 1000*Math.random()));
  const assignment = await retryPromise(
    async () => unsafeConfirmCondition(prolific_pid, session_id),
    LOCK_TIMEOUT,
  ).catch((error) => {
    console.error("Failed to confirm assignment:\n ",
      error,
      "\n Exiting.");
  });
}
