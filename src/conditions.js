import protobuf from "protobufjs";

// Must update accordingly
const SERVER_PATH = "78.141.233.16";
const SERVER_PORT = "3001";
const SERVER_URL = `http://${SERVER_PATH}:${SERVER_PORT}`;

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

export async function initConditionCounts(ncond = 24) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, nothing to initialize...");
    return Math.floor(Math.random() * ncond);
  }
  // Check if 'conditions' are not already in the batch session
  if (!jatos.batchSession.defined("/conditions")) {
    console.log(
      "No exisiting Batch data found, initializing condition counts...",
    );
    const conditionCounts = Array(ncond).fill(0);
    const batchData = {
      conditions: conditionCounts,
      candidates: {},
    };
    // Put the conditions in the batch session
    await jatos.batchSession
      .setAll(batchData)
      .then(() => {
        console.log("Initialized Batch Data successfully");
      })
      .fail(() => {
        console.error("Cound not init conditions");
      });
  }
}

export async function assignCondition(prolific_id, ncond = 24) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, sampling random condition");
    return Math.floor(Math.random() * ncond);
  }
  console.log("In JATOS, retrieving batch session info...");
  // Already assigned
  if (jatos.batchSession.defined(`/candidates/${prolific_id}`)) {
    const candidate = jatos.batchSession
      .find(`/candidates/${prolific_pid}`)
      .fail(() =>
        console.error(`Found record but could not read ${prolific_id}`),
      );
    return candidate;
  }
  console.log(
    `No candidates assigned to ${prolific_id}; Sampling assignment...`,
  );
  console.log(jatos.batchSession.getAll());
  // Otherwise, sample randomly
  let conditions = jatos.batchSession.find("/conditions");
  console.log("Conditions ", conditions);
  const minCount = Math.min(...conditions);
  const eligibleConditions = conditions.flatMap((c, i) =>
    c === minCount ? i : [],
  );
  console.log(`eligible conditions: ${eligibleConditions}`);
  const candidateCondition =
    eligibleConditions[Math.floor(Math.random() * eligibleConditions.length)];

  console.log(`Selected condition: ${candidateCondition}`);

  await jatos.batchSession
    .add(`/candidates/${prolific_id}`, candidateCondition)
    .fail(() => {
      console.error(`Could not assign ${prolific_id} to ${candidateCondition}`);
    });
  return candidateCondition;
}

export async function confirmCondition(prolific_pid, cond_idx) {
  if (typeof jatos === "undefined") {
    console.log("Not in JATOS, doing nothing.");
    return;
  }
  // No longer in database
  if (!jatos.batchSession.defined(`/candidates/${prolific_pid}`)) {
    console.error(`Condition not confirmable for ${prolific_pid}`);
  }
  const count = jatos.batchSession.find(`/conditions/${cond_idx}`);
  await jatos.batchSession
    .replace(`/conditions/${cond_idx}`, count + 1)
    .then(() => {
      jatos.batchSession.remove(`/candidates/${prolific_pid}`);
    })
    .fail(() => {
      console.error("Cound not update candidates record");
    });
}
