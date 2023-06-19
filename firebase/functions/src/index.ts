import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import * as nodemailer from "nodemailer";

admin.initializeApp();

exports.sendNotificationOnCreation = functions.database
  .ref("Cases/{caseId}")
  .onCreate(async (snapshot, context) => {
    const caseId = context.params.caseId;
    const caseData = snapshot.val();
    console.log(`New case ${caseId}`);

    // Get the destination ID
    const destId = caseData.destination_id;
    const origId = caseData.origin_id;

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

    const mailOptions = {
      from: "openkardio@gmail.com",
      to: email,
      subject: `Nuevo EKG para ${destId}`,
      text: `Un nuevo caso fue enviado desde ${origId}`,
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
