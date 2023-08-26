/* eslint-disable require-jsdoc */
/* eslint-disable max-len */
import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as nodemailer from "nodemailer";
import * as canvas from "canvas";
import * as zlib from "zlib";

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

function normalizeIntArray(array: Int16Array): Float32Array {
  const normalizedArray = new Float32Array(array.length);
  const topOfScale = 26400;

  for (let i = 0; i < array.length; i++) {
    normalizedArray[i] = (array[i]*400) / topOfScale;
  }

  return normalizedArray;
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

    const compressedSignalBytes = caseData.signal;
    const compressedSignalBuffer = Buffer.from(compressedSignalBytes);
    const decompressedSignalBuffer = zlib.inflateSync(compressedSignalBuffer);
    const originalSignal = new Int16Array(decompressedSignalBuffer.buffer).slice(0, Math.trunc(decompressedSignalBuffer.length/2));
    const normalizedSignal = normalizeIntArray(originalSignal);

    console.log("Compressed bytes length:", compressedSignalBytes.length);
    console.log("Compressed buffer length:", compressedSignalBuffer.byteLength);
    console.log("Decompressed length:", decompressedSignalBuffer.buffer.byteLength);
    console.log("Original length:", new Int16Array(decompressedSignalBuffer.buffer));
    // console.log("Original Minimum:", Math.min(...originalSignal));
    // console.log("Original Maximum:", Math.max(...originalSignal));
    // console.log("Normalized Minimum:", Math.min(...normalizedSignal));
    // console.log("Normalized Maximum:", Math.max(...normalizedSignal));

    // Create a canvas
    const graphCanvas = canvas.createCanvas(2540, 440);
    const ctx = graphCanvas.getContext("2d");
    ctx.fillStyle = "rgb(255,217,217)";
    ctx.fillRect(0, 0, 2540, 440);
    // Draw graph using basic functions

    ctx.strokeStyle = "rgba(220,153,153,0.9)";

    for (let i = 0; i <= 250; i++) {
      // Vertical Lines
      ctx.beginPath();
      ctx.lineWidth = i%5 == 0 ? 2 : 1;
      ctx.moveTo(i*10+20, 20);
      ctx.lineTo(i*10+20, 420);
      ctx.stroke();
    }
    for (let i = 0; i <= 40; i++) {
      // Horizontal Lines
      ctx.beginPath();
      ctx.lineWidth = i%5 == 0 ? 2 : 1;
      ctx.moveTo(20, i*10+20);
      ctx.lineTo(2520, i*10+20);
      ctx.stroke();
    }

    ctx.strokeStyle = "black";
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.moveTo(20, graphCanvas.height/2);
    for (let i = 0; i < 193; i++) {
      ctx.lineTo(i * ((graphCanvas.width - 40) / (sampleRate*10)) + 20, i <= 38 || i > 96 ? graphCanvas.height/2 : graphCanvas.height/2 - 100);
    }
    for (let i = 1; i < normalizedSignal.length; i++) {
      ctx.lineTo(i * ((graphCanvas.width - 40) / (sampleRate*10)) + 20 + 100, graphCanvas.height - 20 - normalizedSignal[i]);
    }
    ctx.stroke();

    ctx.fillStyle = "rgb(0,0,0)";
    ctx.font = "11pt sans-serif";
    ctx.fillText(`Paciente: ${patientName}`, 20, 16);
    ctx.fillText(`0.2 s/div - 0.5 mV/div  |  Caso #${caseId}  |  Fecha: ${created}`, 20, graphCanvas.height - 4);

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
        user: "openkardio@gmail.com",
        pass: functions.config().gmail.password,
      },
    });

    const htmlContent = `
<p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DATOS DEL PACIENTE</strong></span></p>

<table border="1" cellpadding="1" cellspacing="1" style="width:438.6px">
<tbody>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Unidad de Salud</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${origId}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Nombre del paciente</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${patientName}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Edad</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${patientAge} años</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Expediente</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${patientRecord}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Doc. Identidad</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${patientIdentification}</span></td>
</tr>
</tbody>
</table>

<p>&nbsp;</p>

<p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DETALLES DEL EXAMEN</strong></span></p>

<table border="1" cellpadding="1" cellspacing="1" style="width:438.6px">
<tbody>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>ID del Caso</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${caseId}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Fecha y Hora</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${created}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>SpO2</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${spo2.toString()} %</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Peso</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${weight.toString()} lbs</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Presión</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${pressure}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Ritmo Cardiaco</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${bpm.toString()} bpm</span></td>
</tr>

<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Derivaciones</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${leads}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Tasa de muestreo</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${sampleRate.toString()} sps</span></td>
</tr>

</tbody>
</table>

<p>✅<span style="font-family:Verdana,Geneva,sans-serif">Ingrese a la aplicaci&oacute;n de <strong>OpenKardio</strong> para revisar el ex&aacute;men.</span></p>

<p>&nbsp;</p>
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
      from: "openkardio@gmail.com",
      to: email,
      replyTo: origEmail.length ? origEmail : "openkardio@gmail.com",
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


// export const onMessageUpdate = functions.database
//   .ref("Cases/{caseId}")
//   // eslint-disable-next-line @typescript-eslint/no-unused-vars
//   .onUpdate((change, context) => {
//     const caseId = context.params.caseId;
//     console.log(`Edited case ${caseId}`);
//     const after = change.after.val();


//     const timeEdited = Date.now();
//     return null;
//   });
