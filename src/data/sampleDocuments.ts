import { SevakAnalysisResult, SupportedLanguage } from '../types';

export const SAMPLE_DOCUMENTS: Record<string, SevakAnalysisResult> = {
  echallan: {
    id: 'doc-echallan-01',
    documentTitle: 'Traffic E-Challan Notice (Section 133)',
    category: 'Traffic Police Notice',
    originalFileName: 'Delhi_Traffic_Police_Challan_DL10CXXXX.pdf',
    fileSize: '1.4 MB',
    fileType: 'application/pdf',
    uploadDate: 'Just now',
    confidenceScore: 98,
    classificationConfidence: 1.0,
    isDemoFallback: true,
    what: {
      summary: 'Aapki gaadi par over-speeding aur red-light jump ka Rs. 2,000 ka e-challan kata hai.',
      details: 'Notice ke anusaar, Ring Road (AIIMS ke paas) par automated camera ne 12:45 PM par speed limit 50 km/h ke badle 74 km/h record ki hai.',
    },
    why: {
      significance: 'Ye official traffic notice hai. Time par clear na karne par Virtual Court mein bheja ja sakta hai.',
      urgencyReason: 'Late fees ya RC (Registration Certificate) par non-clearance hold lagne ka risk hota hai.',
    },
    nextSteps: [
      {
        step: 1,
        title: 'Challan Photo & Proof Check Karein',
        description: 'Delhi Traffic Police ya Parivahan portal par jakar photographic proof verify karein ki gaadi aapki hi thi.',
        actionUrl: 'https://echallan.parivahan.gov.in',
      },
      {
        step: 2,
        title: 'Virtual Court ya Online Pay Option Chunein',
        description: 'Agar galti sahi hai, to official parivahan portal se direct net banking/UPI se payment karein.',
        actionUrl: 'https://vcourts.gov.in',
      },
      {
        step: 3,
        title: 'Payment Receipt Save & Download Karein',
        description: 'Successful transaction ke baad digital receipt save karke gaddi ke records mein rakhein.',
      },
    ],
    rights: {
      title: 'Aapke Adhikar (Citizen Rights)',
      safeguards: [
        'Agar photo mein gaadi ka number plate galat padha gaya hai, to aap online grievance dispute file kar sakte hain.',
        'Police bina hearing ya notice ke sidhe gaadi impound nahi kar sakti.',
        'Aapko Virtual Court mein Lok Adalat ya contest karne ka poora adhikar hai.',
      ],
      disclaimer: 'SEVAK legal advisory nahi deta. Kisi sankoch ki sthiti mein advocate ya legal aid se paramarsh lein.',
    },
    deadline: {
      hasDeadline: true,
      date: '21 November 2026',
      daysRemaining: 15,
      urgencyLevel: 'high',
      consequenceText: '15 din ke baad notice Virtual Metropolitan Court ko forward ho sakta hai.',
    },
    source: {
      issuingAuthority: 'Delhi Traffic Police, Headquarters',
      legalSection: 'Motor Vehicles Act 1988, Section 133 / 183',
      referenceNumber: 'DL-CH-2026-8849201',
      officialPortalUrl: 'https://echallan.parivahan.gov.in',
    },
    voiceSummaries: {
      hinglish: 'Namaste! Main SEVAK hoon. Aapke document mein Delhi Traffic Police ka over-speeding challan hai, total do hazaar rupaye ka. Iska last date 21 November hai. Aap parivahan website par jakar photo proof check kar sakte hain aur online pay kar sakte hain.',
      hindi: 'नमस्ते! मैं सेवक हूँ। आपके दस्तावेज़ में दिल्ली ट्रैफ़िक पुलिस द्वारा 2,000 रुपये का चालान जारी किया गया है। इसकी अंतिम तिथि 21 नवंबर है। आप परिवहन पोर्टल पर जाकर फ़ोटो जांच सकते हैं और भुगतान कर सकते हैं।',
      english: 'Hello! I am SEVAK. This document is an official traffic e-challan of Rs. 2,000 issued for over-speeding. The due date for resolution is November 21st. You can verify the camera capture on the Parivahan portal and settle online.',
      bhojpuri: 'प्रणाम! हम सेवक बानी। रउआ के ई कागज दिल्ली ट्रैफिक पुलिस के चालान ह, दु हजार रुपिया के जुर्माना लागल बा। 21 नवंबर से पहिले भुगतान करे के बाटे। परिवहन वेबसाइट पर जाके फोटो देख सकीं ले।',
      maithili: 'प्रणाम! हम सेवक छी। अहाँक ई दस्तावेज दिल्ली ट्रैफिक पुलिसक 2,000 टकाक चालान अछि। 21 नवम्बर धरि भुगतान करबाक अछि। परिवहन पोर्टल पर जा कए फोटो जाँचि सकैत छी।',
    },
    citations: [
      { claim: 'Vehicle recorded at 74 km/h in a 50 km/h speed zone near AIIMS', sourceLocation: 'Page 1, Paragraph 2' },
      { claim: 'Compound penalty of Rs. 2,000 imposed under Section 183 MV Act', sourceLocation: 'Page 1, Paragraph 4' },
      { claim: 'Notice dispute or resolution window active for 15 days', sourceLocation: 'Page 2, Paragraph 1' },
    ],
  },

  bank_kyc: {
    id: 'doc-bank-01',
    documentTitle: 'Bank Re-KYC Update & Account Hold Warning',
    category: 'Banking & KYC',
    originalFileName: 'SBI_Savings_ReKYC_Notice_Nov2026.pdf',
    fileSize: '820 KB',
    fileType: 'application/pdf',
    uploadDate: 'Just now',
    confidenceScore: 96,
    classificationConfidence: 1.0,
    isDemoFallback: true,
    what: {
      summary: 'Bank aapke savings account ke periodic Re-KYC verification ke liye documents maang raha hai.',
      details: 'RBI guidelines ke tahet har 3-5 saal mein high/medium risk profiles ka KYC update anivarya hota hai. Bank ne Aadhaar, PAN aur current address proof manga hai.',
    },
    why: {
      significance: 'KYC complete na hone par UPI transactions aur debit card temporary freeze ho sakte hain.',
      urgencyReason: 'Notice date ke 30 din ke andar agar update nahi hua, to debit freeze lag sakta hai.',
    },
    nextSteps: [
      {
        step: 1,
        title: 'Video KYC ya YONO/NetBanking Check Karein',
        description: 'Agar aapka Aadhaar phone number se linked hai, to ghar baithe video KYC ya official bank app se submit karein.',
      },
      {
        step: 2,
        title: 'Official Branch ya KYC Portal par hi Upload Karein',
        description: 'Kabhi bhi SMS ya WhatsApp link par Aadhaar/OTP share na karein. Sirf official branch ya portal use karein.',
      },
      {
        step: 3,
        title: 'Acknowledgment Token Receive Karein',
        description: 'Submission ke baad bank se 10-digit SRN (Service Request Number) sms/email par confirm karein.',
      },
    ],
    rights: {
      title: 'Aapke Adhikar (Banking Protection)',
      safeguards: [
        'Bank aapke paise zabt nahi kar sakta; sirf temporary debit freeze lagta hai.',
        'Aadhaar ke badle Passport, Voter ID ya Driving License bhi valid Official Valid Document (OVD) hain.',
        'Senior citizens aur physically challenged vyakti home visit verification request kar sakte hain.',
      ],
      disclaimer: 'Bank kabhi bhi phone par password ya OTP nahi maangta. Cyber fraud se savdhan rahein.',
    },
    deadline: {
      hasDeadline: true,
      date: '05 December 2026',
      daysRemaining: 29,
      urgencyLevel: 'medium',
      consequenceText: '30 din baad net banking aur UPI par outward remittance hold ho sakta hai.',
    },
    source: {
      issuingAuthority: 'State Bank of India — Retail Banking Operations',
      legalSection: 'RBI Master Direction - KYC Direction, 2016 (Updated 2025)',
      referenceNumber: 'SBI-KYC-RET-498271',
      officialPortalUrl: 'https://www.onlinesbi.sbi',
    },
    voiceSummaries: {
      hinglish: 'Namaste! SEVAK bol raha hoon. Ye aapke bank ka regular Re-KYC notice hai. Bank ne aapka Aadhaar aur PAN verify karne ko kaha hai. Kisi fake link par click mat kijiye, seedhe branch ya official bank app se 5 December se pehle submit karein.',
      hindi: 'नमस्ते! मैं सेवक हूँ। यह आपके बैंक का नियमित री-केवाईसी नोटिस है। बैंक ने आधार और पैन सत्यापन की मांग की है। 5 दिसंबर से पहले बैंक शाखा या आधिकारिक ऐप के माध्यम से अपडेट करें।',
      english: 'Hello! This is SEVAK. This document is a mandatory Re-KYC update request from your bank. To avoid any temporary freeze on your UPI or card, please submit your Aadhaar and PAN through the official app or branch by December 5th.',
      bhojpuri: 'प्रणाम! हम सेवक बोलत बानी। ई राउर बैंक के री-केवाईसी के नोटिस ह। आधार आ पैन कार्ड बैंक में जमा करे के बा। 5 दिसंबर तक तारीख बा, कवनो अनजान लिंक पर ओटीपी मत दिहीं।',
      maithili: 'प्रणाम! हम सेवक छी। ई अहाँक बैंकक री-केवाईसी सूचना अछि। बैंक आधार आ पैन कार्डक नवीनीकरण मांगि रहल अछि। 5 दिसम्बर सँ पूर्व आधिकारिक शाखा में जमा करू।',
    },
    citations: [
      { claim: 'Mandatory Re-KYC update requested under RBI Master Direction 2016', sourceLocation: 'Page 1, Paragraph 1' },
      { claim: 'Outward remittance debit hold applied if pending past 30 days', sourceLocation: 'Page 1, Paragraph 3' },
      { claim: 'Alternative valid documents include Passport, Voter ID, and DL', sourceLocation: 'Page 2, Paragraph 2' },
    ],
  },

  tax_notice: {
    id: 'doc-tax-01',
    documentTitle: 'Income Tax Clarification Notice (Section 142(1))',
    category: 'Income Tax Department',
    originalFileName: 'ITD_Notice_Sec142_AY2025-26.pdf',
    fileSize: '2.1 MB',
    fileType: 'application/pdf',
    uploadDate: 'Just now',
    confidenceScore: 97,
    classificationConfidence: 1.0,
    isDemoFallback: true,
    what: {
      summary: 'Income Tax Department ne Assessment Year ke return mein ek clarification maanga hai.',
      details: 'Notice ke anusaar, savings interest aur high-value cash deposit ke data mein AIS (Annual Information Statement) se Rs. 45,000 ka difference dikh raha hai.',
    },
    why: {
      significance: 'Ye inquiry notice hai, raid ya penalty notice nahi hai. Simple online response dene se matter solve ho jata hai.',
      urgencyReason: 'Time par jawab na dene par Assessing Officer ex-parte order pass kar sakta hai.',
    },
    nextSteps: [
      {
        step: 1,
        title: 'e-Filing Portal par Notice Check Karein',
        description: 'incometax.gov.in par login karke "Pending Actions > e-Proceedings" tab mein notice open karein.',
        actionUrl: 'https://eportal.incometax.gov.in',
      },
      {
        step: 2,
        title: 'AIS/TIS aur Bank Statement Match Karein',
        description: 'Apne saare savings accounts ki interest certificates download karke reported figure tally karein.',
      },
      {
        step: 3,
        title: 'Online Clarification Submit Karein',
        description: 'e-Proceedings portal par hi explanation upload karein ya Chartered Accountant / Tax Practitioner se salah lein.',
      },
    ],
    rights: {
      title: 'Aapke Adhikar (Taxpayer Charter)',
      safeguards: [
        'Notice par Document Identification Number (DIN) hona anivarya hai; bina DIN notice invalid hota hai.',
        'Aapko portal ke through additonal time (adjournment) mangne ka adhikar hai.',
        'Faceless assessment scheme ke antargat kisi officer ke office jaane ki zaroorat nahi hai.',
      ],
      disclaimer: 'SEVAK official tax advisor nahi hai. Complex discrepancies ke liye registered CA se consult karein.',
    },
    deadline: {
      hasDeadline: true,
      date: '18 November 2026',
      daysRemaining: 12,
      urgencyLevel: 'high',
      consequenceText: '12 din ke andar jawab na aane par Section 271(1)(b) ke tahat penalty intimation aa sakti hai.',
    },
    source: {
      issuingAuthority: 'Income Tax Department, National Faceless Assessment Centre (NeFAC)',
      legalSection: 'Income Tax Act 1961, Section 142(1)',
      referenceNumber: 'ITBA/AST/F/142(1)/2026-27/1049281',
      officialPortalUrl: 'https://eportal.incometax.gov.in',
    },
    voiceSummaries: {
      hinglish: 'Namaste! Main SEVAK hoon. Aapko Income Tax Department se Section 142(1) ka inquiry notice mila hai. Bank interest figure mein thoda antar hai. Ghabraiye mat, ye raid nahi hai. 18 November se pehle income tax portal par jakar online explanation upload kar dijiye.',
      hindi: 'नमस्ते! मैं सेवक हूँ। यह आयकर विभाग से धारा 142(1) का स्पष्टीकरण नोटिस है। बचत खाते के ब्याज में कुछ विसंगति है। 18 नवंबर से पहले आधिकारिक आयकर पोर्टल पर जाकर ऑनलाइन जवाब दें।',
      english: 'Hello! I am SEVAK. You have received an inquiry notice under Section 142(1) regarding minor discrepancy in reported interest income. Please do not worry—this is a routine query. You can submit your online response via the e-filing portal before November 18th.',
      bhojpuri: 'प्रणाम! हम सेवक बानी। इनकम टैक्स विभाग से धारा 142(1) के नोटिस आइल बा। बैंक ब्याज के रकम में कुछु फर्क बा। डेराए के कवनो बात नइखे, 18 नवंबर ले सरकारी पोर्टल पर सफाई दे दीहीं।',
      maithili: 'प्रणाम! हम सेवक छी। ई आयकर विभागक धारा 142(1) केर पूछताछ सूचना अछि। बचत खातक ब्याज में किछु अंतर अछि। 18 नवम्बर सँ पूर्व आयकर पोर्टल पर अनलाइन उत्तर दियौक।',
    },
    citations: [
      { claim: 'Notice issued under Section 142(1) for inquiry into reported interest income', sourceLocation: 'Page 1, Paragraph 1' },
      { claim: 'Mandatory Document Identification Number (DIN) generated by NeFAC', sourceLocation: 'Page 1, Paragraph 3' },
      { claim: 'Online clarification submission requested before November 18, 2026', sourceLocation: 'Page 2, Paragraph 2' },
    ],
  },
};
