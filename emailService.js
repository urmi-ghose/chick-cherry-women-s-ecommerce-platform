const express = require("express");
const nodemailer = require("nodemailer");
const cors = require("cors");
require("dotenv").config();

const app = express();
const PORT = process.env.EMAIL_PORT || 3001;
const EMAIL_USER = process.env.EMAIL_USER;
const EMAIL_APP_PASSWORD = process.env.EMAIL_APP_PASSWORD;

// === Transporter creation using Gmail SMTP ===
const createTransporter = () => {
  return nodemailer.createTransport({
    host: "smtp.gmail.com",
    port: 587, // 587 = STARTTLS, 465 = SSL/TLS
    secure: false, // false for port 587 (STARTTLS)
    auth: {
      user: EMAIL_USER,
      pass: EMAIL_APP_PASSWORD,
    },
  });
};

// Middleware
app.use(cors());
app.use(express.json());

// Simple startup verification to fail fast if SMTP creds are wrong
const verifyTransporter = async () => {
  const transporter = createTransporter();
  try {
    await transporter.verify(); // checks connection and authentication
    console.log("SMTP connection verified");
  } catch (err) {
    console.error(
      "SMTP verify failed — check EMAIL_USER / EMAIL_APP_PASSWORD and network:",
      err.message
    );
    // don't exit; you may want service to continue for local testing — comment out if you prefer process.exit(1)
  }
};

// Email sending endpoint
app.post("/send-email", async (req, res) => {
  const { to, subject, html, text } = req.body;

  if (!to || !subject || (!html && !text)) {
    return res.status(400).json({
      success: false,
      message: "Missing required fields: to, subject, and html or text",
    });
  }

  const transporter = createTransporter();

  const mailOptions = {
    from: EMAIL_USER,
    to: to,
    subject: subject,
    html: html,
    text: text,
  };

  try {
    const info = await transporter.sendMail(mailOptions);
    console.log("Email sent successfully:", info.messageId);
    res.json({
      success: true,
      message: "Email sent successfully",
      messageId: info.messageId,
    });
  } catch (error) {
    console.error("Email sending failed:", error);
    res.status(500).json({
      success: false,
      message: "Failed to send email",
      error: error && error.message ? error.message : String(error),
    });
  }
});

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ status: "Email service is running" });
});

// Start server and verify SMTP once
app.listen(PORT, async () => {
  console.log(`Email service running on port ${PORT}`);
  await verifyTransporter();
});

module.exports = app;