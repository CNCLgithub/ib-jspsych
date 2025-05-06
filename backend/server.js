// from GROK:
// https://grok.com/share/c2hhcmQtMg%3D%3D_d2247606-5a98-4d34-bdea-3c112c7747c7

// Change accordingly
const server_address = "78.141.233.16";
const port = 3001;

const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");
const app = express();

// Enable CORS for JATOS frontend
app.use(cors());
app.use(express.json());

const nscenes = 6;
const nperscene = 4;
const nconditions = nscenes * nperscene;
const conditions = [...Array(nconditions).keys()].map((x) => x + 1);

// Initialize SQLite database
const db = new sqlite3.Database("./conditions.db", (err) => {
  if (err) {
    console.error("Error opening database:", err.message);
  } else {
    console.log("Connected to SQLite database.");
    // Create conditions table (completed counts)
    db.run(
      `
            CREATE TABLE IF NOT EXISTS conditions (
                condition INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0
            )
        `,
      (err) => {
        if (err) {
          console.error("Error creating conditions table:", err.message);
        } else {
          // Initialize conditions
          conditions.forEach((cond) => {
            db.run(
              `INSERT OR IGNORE INTO conditions (condition, count) VALUES (?, 0)`,
              [cond],
              (err) => {
                if (err)
                  console.error("Error initializing condition:", err.message);
              },
            );
          });
        }
      },
    );
    // Create pending_assignments table (temporary assignments)
    db.run(
      `
            CREATE TABLE IF NOT EXISTS pending_assignments (
                prolific_pid TEXT PRIMARY KEY,
                condition INTEGER NOT NULL,
                timestamp INTEGER NOT NULL
            )
        `,
      (err) => {
        if (err) {
          console.error(
            "Error creating pending_assignments table:",
            err.message,
          );
        }
      },
    );
  }
});

// Endpoint to assign a candidate condition
app.get("/candidate-condition", async (req, res) => {
  const prolific_pid = req.query.prolific_pid || "unknown";
  try {
    // Check if participant already has a pending assignment
    const existingAssignment = await new Promise((resolve, reject) => {
      db.get(
        `SELECT condition FROM pending_assignments WHERE prolific_pid = ?`,
        [prolific_pid],
        (err, row) => {
          if (err) reject(err);
          else resolve(row);
        },
      );
    });

    if (existingAssignment) {
      // Return existing candidate condition
      return res.json({ condition: existingAssignment.condition });
    }

    // Get current condition counts (completed)
    const rows = await new Promise((resolve, reject) => {
      db.all("SELECT condition, count FROM conditions", [], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });

    // Find condition with fewest completed participants
    let minCount = Math.min(...rows.map((row) => row.count));
    let eligibleConditions = rows
      .filter((row) => row.count === minCount)
      .map((row) => row.condition);
    let candidateCondition =
      eligibleConditions[Math.floor(Math.random() * eligibleConditions.length)];

    // Store pending assignment
    await new Promise((resolve, reject) => {
      db.run(
        `INSERT INTO pending_assignments (prolific_pid, condition, timestamp) VALUES (?, ?, ?)`,
        [prolific_pid, candidateCondition, Date.now()],
        (err) => {
          if (err) reject(err);
          else resolve();
        },
      );
    });

    // Return candidate condition
    res.json({ condition: candidateCondition });
  } catch (error) {
    console.error("Error assigning candidate condition:", error.message);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Endpoint to confirm a condition assignment
app.post("/confirm-condition", async (req, res) => {
  console.log(req.body);
  const { prolific_pid, condition } = req.body;
  if (!prolific_pid || !condition) {
    return res.status(400).json({ error: "Missing prolific_pid or condition" });
  }

  try {
    // Verify pending assignment
    const pending = await new Promise((resolve, reject) => {
      db.get(
        `SELECT condition FROM pending_assignments WHERE prolific_pid = ?`,
        [prolific_pid],
        (err, row) => {
          if (err) reject(err);
          else resolve(row);
        },
      );
    });

    if (!pending || pending.condition !== condition) {
      return res
        .status(400)
        .json({ error: "Invalid or missing pending assignment" });
    }

    // Increment count for confirmed condition
    await new Promise((resolve, reject) => {
      db.run(
        `UPDATE conditions SET count = count + 1 WHERE condition = ?`,
        [condition],
        (err) => {
          if (err) reject(err);
          else resolve();
        },
      );
    });

    // Remove pending assignment
    await new Promise((resolve, reject) => {
      db.run(
        `DELETE FROM pending_assignments WHERE prolific_pid = ?`,
        [prolific_pid],
        (err) => {
          if (err) reject(err);
          else resolve();
        },
      );
    });

    res.json({ status: "success" });
  } catch (error) {
    console.error("Error confirming condition:", error.message);
    res.status(500).json({ error: "Internal server error" });
  }
});

// Start server
app.listen(port, () => {
  console.log(`Server running at http://${server_address}:${port}`);
});
