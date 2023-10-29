/* eslint-disable camelcase */
/* eslint-disable require-jsdoc */
/* eslint-disable max-len */
import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as nodemailer from "nodemailer";
import * as canvas from "canvas";
import * as zlib from "zlib";
import * as moment from "moment-timezone";
import * as cors from "cors";

admin.initializeApp();

function parseDateString(dateString: string): Date {
  const parts = dateString.split("-");

  const day = parseInt(parts[0]);
  const month = parseInt(parts[1]) - 1; // Months in JavaScript are 0-indexed
  const year = parseInt(parts[2]);

  return new Date(year, month, day);
}

function calculateAge(birthdate: Date): number {
  const currentDate = new Date();

  const yearsDiff = currentDate.getFullYear() - birthdate.getFullYear();
  const currentMonth = currentDate.getMonth();
  const birthMonth = birthdate.getMonth();

  // Adjust age based on birth month
  if (currentMonth < birthMonth || (currentMonth === birthMonth && currentDate.getDate() < birthdate.getDate())) {
    return yearsDiff - 1;
  }

  return yearsDiff;
}

function normalizeIntArray(array: Int16Array, gain: number, pixelsPerMv: number): Float32Array {
  const normalizedArray = new Float32Array(array.length);

  for (let i = 0; i < array.length; i++) {
    normalizedArray[i] = (array[i]*pixelsPerMv) / gain;
  }

  return normalizedArray;
}

function generateTimestamp(): string {
  // Get the current timestamp in UTC
  const utcTimestamp = Date.now();

  // Convert to the desired timezone (UTC-6)
  const utcMinus6Timestamp = moment(utcTimestamp).tz("America/Managua");

  // Format the timestamp in ISO format
  const isoTimestamp = utcMinus6Timestamp.format("YYYY-MM-DDTHH:mm:ss");

  return isoTimestamp;
}

exports.sendNotificationOnCreation = functions.database
  .ref("Cases/{caseId}")
  .onCreate(async (snapshot, context) => {
    const caseId = context.params.caseId;
    const caseData = snapshot.val();
    console.log(`New case ${caseId}`);

    // Get the destination ID
    const destId = caseData.destination_id;
    const origId = caseData.origin_id;
    const created = caseData.created;
    const patientName = caseData.patient_first_name + " " + caseData.patient_last_name;
    const patientRecord = caseData.patient_record;
    const patientAge = calculateAge(parseDateString(caseData.patient_birth_date)).toString();
    const patientIdentification = caseData.patient_identification;
    const sampleRate = caseData.sample_rate;
    const leads = caseData.leads;
    const spo2 = caseData.spo2;
    const weight = caseData.weight_pd;
    const pressure = caseData.pressure;
    const bpm = caseData.bpm;
    const signalGain = caseData.gain;
    const notes = caseData.notes;
    const rPeaks = caseData.rpeaks;

    // Graph Constants
    const graphMargin = 20;
    const graphWidth = 2500;
    const graphHeight = 300;
    const pixelsPerSubdiv = 10;

    const compressedSignalBytes = caseData.signal;
    const compressedSignalBuffer = Buffer.from(compressedSignalBytes);
    const decompressedSignalBuffer = zlib.inflateSync(compressedSignalBuffer);
    const originalSignal = new Int16Array(decompressedSignalBuffer.buffer).slice(0, Math.trunc(decompressedSignalBuffer.length/2));
    const normalizedSignal = normalizeIntArray(originalSignal, signalGain, 10*pixelsPerSubdiv);

    console.log("Compressed bytes length:", compressedSignalBytes.length);
    console.log("Compressed buffer length:", compressedSignalBuffer.byteLength);
    console.log("Decompressed length:", decompressedSignalBuffer.buffer.byteLength);
    // console.log("Original length:", new Int16Array(decompressedSignalBuffer.buffer));
    // console.log("Original Minimum:", Math.min(...originalSignal));
    // console.log("Original Maximum:", Math.max(...originalSignal));
    // console.log("Normalized Minimum:", Math.min(...normalizedSignal));
    // console.log("Normalized Maximum:", Math.max(...normalizedSignal));
    console.log("Peaks:", rPeaks);

    // Create a canvas
    const graphCanvas = canvas.createCanvas(graphWidth + 2*graphMargin, graphHeight + 2*graphMargin);
    const ctx = graphCanvas.getContext("2d");
    ctx.fillStyle = "rgb(255,217,217)";
    ctx.fillRect(0, 0, graphWidth + 2*graphMargin, graphHeight + 2*graphMargin);
    // Draw graph using basic functions

    ctx.strokeStyle = "rgba(220,153,153,0.9)";

    for (let i = 0; i <= Math.floor(graphWidth/pixelsPerSubdiv); i++) {
      // Vertical Lines
      ctx.beginPath();
      ctx.lineWidth = i%5 == 0 ? 2 : 0.75;
      ctx.moveTo(i*pixelsPerSubdiv+graphMargin, graphMargin);
      ctx.lineTo(i*pixelsPerSubdiv+graphMargin, graphHeight + graphMargin);
      ctx.stroke();
    }
    for (let i = 0; i <= Math.floor(graphHeight/pixelsPerSubdiv); i++) {
      // Horizontal Lines
      ctx.beginPath();
      ctx.lineWidth = i%5 == 0 ? 2 : 0.75;
      ctx.moveTo(graphMargin, i*pixelsPerSubdiv+graphMargin);
      ctx.lineTo(graphWidth + graphMargin, i*pixelsPerSubdiv+graphMargin);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(25,25,25,0.3)";
    ctx.fillStyle = "rgb(0,0,0)";
    ctx.font = "11pt sans-serif";
    for (let i = 1; i < rPeaks.length; i++) {
      ctx.beginPath();
      ctx.lineWidth = 3;
      ctx.moveTo(((rPeaks[i] + 193)*(graphCanvas.width - 2*graphMargin) / (sampleRate*10.0)) + graphMargin, graphMargin);
      ctx.lineTo(((rPeaks[i] + 193)*(graphCanvas.width - 2*graphMargin) / (sampleRate*10.0)) + graphMargin, graphHeight + graphMargin);
      ctx.stroke();
      ctx.fillText(`${Math.floor(rPeaks[i]*1000/sampleRate + 400)} ms`, (rPeaks[i] + 193)*(graphCanvas.width - 40) / (sampleRate*10.0), graphCanvas.height - 4);
    }

    ctx.strokeStyle = "black";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.moveTo(20, graphCanvas.height/2);
    for (let i = 0; i < 193; i++) {
      ctx.lineTo(i * ((graphWidth) / (sampleRate*10)) + graphMargin, i <= 38 || i > 96 ? graphCanvas.height/2 : graphCanvas.height/2 - 10*pixelsPerSubdiv);
    }
    for (let i = 1; i < normalizedSignal.length; i++) {
      ctx.lineTo(i * ((graphCanvas.width - 40) / (sampleRate*10)) + 20 + 100, graphCanvas.height - 20 - (normalizedSignal[i] + graphHeight/2));
    }
    ctx.stroke();

    ctx.fillStyle = "rgb(0,0,0)";
    ctx.font = "11pt sans-serif";
    ctx.fillText(`Paciente: ${patientName} |  Caso #${caseId}  |  Fecha: ${created}`, 20, 16);
    ctx.fillText("0.2 s/div - 0.5 mV/div", 20, graphCanvas.height - 4);

    // Convert canvas to PNG buffer
    const graphImageBuffer = graphCanvas.toBuffer();

    // Get the email address
    const emailRef = admin.database().ref(`Hospitals/${destId}/email`);
    const emailSnapshot = await emailRef.once("value");
    const email = emailSnapshot.val();

    // Send email notification
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: functions.config().gmail.address,
        pass: functions.config().gmail.password,
      },
    });

    const htmlContent = `
<html>
<head>
  <style>
    .button {
      display: inline-block;
      background-color: #afcce9;
      color: #0e0e0e;
      padding: 10px 20px;
      text-decoration: none;
      border-radius: 5px;
    }
  </style>
</head>
<body>

  <p><span style="font-family:Verdana,Geneva,sans-serif"><strong>NUEVO EXAMEN</strong></span></p>

  <p>✅<span style="font-family:Verdana,Geneva,sans-serif"> Ingrese a la aplicaci&oacute;n de <strong>OpenKardio</strong> para revisar el examen.</span></p>
  <p>✅<span style="font-family:Verdana,Geneva,sans-serif"> Alternativamente, puedes enviar tu diagn&oacute;stico en el siguiente enlace:</span></p>

  <a class="button" href="${functions.config().form.url}/diagnosis-form.html?examId=${caseId}"><strong>Diagnosticar examen</strong></a>
  <p>&nbsp;</p>

  <p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DATOS DEL PACIENTE</strong></span></p>

  <table border="1" cellpadding="1" cellspacing="1" style="width:450px">
  <tbody>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Unidad de Salud</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${origId}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Nombre del paciente</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${patientName}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Edad</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${patientAge} años</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Expediente</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${patientRecord}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Doc. Identidad</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${patientIdentification}</span></td>
  </tr>
  </tbody>
  </table>

  <p>&nbsp;</p>

  <p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DETALLES DEL EXAMEN</strong></span></p>

  <table border="1" cellpadding="1" cellspacing="1" style="width:438.6px">
  <tbody>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>ID del Caso</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${caseId}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Fecha y Hora</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${created}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>SpO2</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${spo2.toString()} %</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Peso</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${weight.toString()} lbs</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Presión</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${pressure}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Ritmo Cardiaco</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${bpm.toString()} bpm</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Derivaciones</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${leads}</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Tasa de muestreo</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${sampleRate.toString()} sps</span></td>
  </tr>
  <tr>
  <td style="width:130px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Comentarios</strong></span></td>
  <td style="width:320px"><span style="font-family:Verdana,Geneva,sans-serif">${notes}</span></td>
  </tr>
  </tbody>
  </table>

  <p>&nbsp;</p>
</body>
    `;

    let origEmail = "";

    try {
      const hcSnapshot = await admin.database().ref(`/HCenters/${origId}`).once("value");
      const hcData = hcSnapshot.val();

      if (hcData) {
        origEmail = hcData.email;
      } else {
        console.error("Health Center not found");
      }
    } catch (error) {
      console.error("Error getting Health center:", error);
    }

    const mailOptions = {
      from: functions.config().gmail.address,
      to: email,
      replyTo: origEmail.length ? origEmail : functions.config().gmail.address,
      subject: `Nuevo EKG para ${destId}`,
      html: htmlContent,
      attachments: [{
        filename: `ekg_${caseId}.png`,
        content: graphImageBuffer,
      }],
    };

    await transporter.sendMail(mailOptions);

    console.log("Email sent successfully");
  });

// Firebase Cloud Function to handle diagnosis submission
exports.submitDiagnosis = functions.https.onRequest(async (req, res) => {
  cors({origin: true})(req, res, async () => {
    const examId = req.body.examId;
    const diagnosis = req.body.diagnosis;
    const timestamp = generateTimestamp();

    const updateObj = {
      diagnostic: diagnosis,
      status: "EVALUADO",
      modified: timestamp,
      diagnosed: timestamp,
    };

    // Update the diagnosis field in the Realtime Database
    const examRef = admin.database().ref(`/Cases/${examId}`);
    examRef.update(updateObj)
      .then(() => {
        res.status(200).send("Diagnosis submitted successfully");
      })
      .catch((error) => {
        console.error("Error receiving diagnostic:", error);
        res.status(500).send("Error submitting diagnosis");
      });

    try {
      const origId = (await examRef.once("value")).val().origin_id;
      const hcSnapshot = await admin.database().ref(`/HCenters/${origId}`).once("value");
      const hcData = hcSnapshot.val();

      if (hcData) {
        const origEmail = hcData.email;
        // Send email notification
        const transporter = nodemailer.createTransport({
          service: "gmail",
          auth: {
            user: functions.config().gmail.address,
            pass: functions.config().gmail.password,
          },
        });

        const htmlContent = `
        <p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DIAGNÓSTICO DEL EXAMEN ${examId}</strong></span></p>
        <p>&nbsp;</p>
        <p><span style="font-family:Verdana,Geneva,sans-serif">${diagnosis}</span></p>
        <p>&nbsp;</p>
        <p><span style="font-family:Verdana,Geneva,sans-serif">Recibido el ${timestamp}.</span></p>`;

        const mailOptions = {
          from: functions.config().gmail.address,
          to: origEmail,
          subject: `Nuevo Diagnóstico para ${origId}`,
          html: htmlContent,
        };

        await transporter.sendMail(mailOptions);

        console.log("Email sent successfully");
      } else {
        console.error("Health Center not found");
      }
    } catch (error) {
      console.error("Error getting Health center:", error);
    }
  });
});

exports.checkDiagnosisStatus = functions.https.onRequest((req, res) => {
  cors({origin: true})(req, res, async () => {
    try {
      const examId = req.query.examId;

      // Fetch exam data from Realtime Database
      const examSnapshot = await admin
        .database()
        .ref(`/Cases/${examId}`)
        .once("value");
      const exam = examSnapshot.val();

      if (!exam) {
        res.status(404).send("Exam not found");
        return;
      }

      const response = {
        isDiagnosed: exam.status === "EVALUADO",
        diagnostic: exam.diagnostic || null,
      };

      res.json(response);
    } catch (error) {
      console.error("Error:", error);
      res.status(500).send("An error occurred");
    }
  });
});

