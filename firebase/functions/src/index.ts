/* eslint-disable require-jsdoc */
/* eslint-disable max-len */
import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as nodemailer from "nodemailer";

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
<p><span style="font-family:Verdana,Geneva,sans-serif"><strong>DETALLES</strong></span></p>

<table border="1" cellpadding="1" cellspacing="1" style="width:438.6px">
<tbody>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Fecha y Hora</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${created}</span></td>
</tr>
<tr>
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>Origen</strong></span></td>
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
<td style="width:129px"><span style="font-family:Verdana,Geneva,sans-serif"><strong>ID del Caso</strong></span></td>
<td style="width:296px"><span style="font-family:Verdana,Geneva,sans-serif">${caseId}</span></td>
</tr>
</tbody>
</table>

<p>✅<span style="font-family:Verdana,Geneva,sans-serif">Ingrese a la aplicaci&oacute;n de <strong>OpenKardio</strong> para revisar el ex&aacute;men.</span></p>

<p>&nbsp;</p>
    `;

    const mailOptions = {
      from: "openkardio@gmail.com",
      to: email,
      subject: `Nuevo EKG para ${destId}`,
      html: htmlContent,
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
