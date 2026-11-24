# Gold-set spot check
For each item: is the **gold label** right? Items 1-10 are the cases where pipeline and gold disagree; the rest are random agreements.
Mark `OK` or write the correct label.

## 1. document `fil_4xyfltn8`
- **gold:** other   ·  **pipeline:** invoice (by llm)
- gold note: Sales order (GF Distribution/Gramlin), not titled invoice
- your verdict: 

> DOCUMENT Filename: RDR2002148004.pdf Text: SALES ORDER 36228 Order No. Order Date Ship-To Address 8/31/2026 Bill-To Address GF Distribution LLC 3165 Red Hill Ave. Costa Mesa, CA 92626 San Jose Wellness - Harborside San Jose EAZE 1365 N 10th St San Jose CA 95112 USA Att: Joseph Delivery No. San Jose Wellness - Harborside San Jose EAZE 1365 N 10th St San Jose, CA 95112 Delivery date 9/21/2026 PO# Payment Terms NET 60 Shipping Method Sales Rep Dan Gleiberman Distributor Delivery METRC License # C10-0000435-LIC Item no. Amount Price Quantity Item name Species 113922 10 $10.00 $100.00 Sativa Gramlin All-In-One Vape - Blue Dream 1g 113923 20 $10.00 $200.00 Hybrid Gramlin All-In-One Vape - Blueberr

## 2. email `5753e992-8fc5-417d-a2c5-dc17b7067884`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Empty forward; only attachment name 244274.pdf - content unknown | field recheck: bare forward; number matches filename; no amount visible
- your verdict: 

> EMAIL Subject: Fwd: Eaze Hometown Heart East Bay From: Accounts Payable <ap@eaze.com> Attachments: ['244274.pdf'] Body: 

## 3. email `8382af24-190a-450d-95dd-b7cce8bf9f24`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Internal AP batch of 12 Kiva invoice PDFs; empty body | field recheck: bulk forward of 12 invoice PDFs; all 12 filenames have a matching extracted number
- your verdict: 

> EMAIL Subject: kiva From: Accounts Payable <ap@eaze.com> Attachments: ['856968.pdf', '856972.pdf', '856970.pdf', '856967.pdf', '856965.pdf', '856969.pdf', '856971.pdf', '856974.pdf', '856975.pdf', '856966.pdf', '856964.pdf', '856973.pdf'] Body: 

## 4. email `1a4ba218-21aa-4838-b7f5-a0652916b9c8`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Internal forward of Minnesota Paid Leave 'Notice of Amount Due' (state contribution bill); only filename visible - could be past-due notice
- your verdict: 

> EMAIL Subject: Accounting Mail 08/25/2026 From: Kris Trujillo <kris.trujillo@eaze.com> Attachments: ['Minnesota Notice of Amount Due Eaze INC Paid Leave Program 08252026.pdf'] Body: Good afternoon, Here is some mail for Accounting that was picked up at Edgewater yesterday. Thanks! [image: Eaze] <https://www.eaze.com/> Kris Trujillo Specialist, People & Culture [image: Email] kris.trujillo@eaze.com [image: Phone] 720-933-1674 <+7209331674> [image: Vireo] <https://vireogrowth.com/> [image: Glass House Brands] <https://glasshousebrands.com/> [image: Green Dragon] <https://greendragonfl.com/> 

## 5. email `74a7b489-1c2c-49d4-856b-2357560bf9ef`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Internal AP forward of ~18 invoice/PO PDFs, no body; multiple invoices | field recheck: bulk forward of 18 invoice PDFs
- your verdict: 

> EMAIL Subject: Re: CA From: Accounts Payable <ap@eaze.com> Attachments: ['1048272_CAPNA-INC-_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789143154293.pdf', '1048400_Strong-Agronomy-Management-Inc-_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789148447010.pdf', '1047680_Humo-Corp_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789072426407.pdf', '1048206_LP-District-11-Inc-_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789124977198.pdf', '1047956_Pacific-Stone---Twisted-Roots-Inc-_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789081596925.pdf', '1047797_StateHouse_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-1789076173537.pdf', '1047733_EAZE_EAZE-East-Bay-HOMETOWN-HEART-INC-_09-15-2026-17890

## 6. document `fil_4xyrekpg`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: OCR scan of Nabis invoice, order 1030006, total $1,228 not extracted
- your verdict: 

> DOCUMENT Filename: Doc - Aug 24 2026 - 11-40 AM.pdf Text: J ORDER # 1030006 PO/SO PO-151991 Departure Time 08/24/2026 08/24/2026 :: 10:00-11:00 Actual Arrival Time [OO (408) 840-9718 [Email ___| isaac@goheadwaters.com EAZE Orange County | D.B.A. EAZE Orange County Delivery [HEALTHY HEALING HOLISTIC OPTION- ORIGIN: NaBis LA- Garden of Weeden, INC. RECIPIENT: _s, INC] adarens Origin] Nabis LA (Garden of Weede- 9625 & Gertrude Pn g, | Contact_| Cesar Perez 1816 E-Olympic Bld, Los Contact |) 5 Santa Ana, CA 92705 Ferene | (uly 347-1445 Angeles, CA 900 510-394-185 [eae bemeenes pes fen | oe m State Not Available vam -01stLt0 a a ee poles 10-0001 Licerise TRANSFERRING DISTRIBUTOR: Nasirive, LLC db

## 7. email `d4d879f3-e822-44d6-abfd-380fa4a2f0e9`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Internal AP forward of multiple Nabis invoice PDFs, no body | field recheck: bulk forward of 18 invoice PDFs (many unnamed scans)
- your verdict: 

> EMAIL Subject: CA From: Accounts Payable <ap@eaze.com> Attachments: ['1031694_Pacific-Stone---Twisted-Roots-Inc-_Eaze-Van-Nuys-Retail-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787595144586.pdf', '1031830_LP-District-11-Inc-_Eaze-Van-Nuys-Retail-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787595131638.pdf', '1030085_LP-District-11-Inc-_Eaze-Van-Nuys-Delivery-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787594896096.pdf', '1031769_Glass-House-Brands_Eaze-Van-Nuys-Retail-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787595138784.pdf', '1030311_EAZE_Eaze-Van-Nuys-Delivery-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787594884264.pdf', '1030431_Smokiez-ACS-LLC_Eaze-Van-Nuys-Delivery-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787594874904.

## 8. email `43e32690-87f6-4225-b47c-6da8f27f0ca2`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: Nabis shipping confirmation delivering invoice/manifest + COAs; order 1058922 | field recheck: no amount visible in email
- your verdict: 

> EMAIL Subject: #1058922 Shipping Confirmation + COAs: Proof Operations, Inc. <> EAZE San Diego Delivery [ECSD MANAGEMENT LLC] for 09/30/2026 From: <deliveries-socal@nabis.com> Attachments: ['1058922_Proof-Operations-Inc-_EAZE-San-Diego-Delivery-ECSD-MANAGEMENT-LLC-_09-30-2026-1790621026041.pdf'] Body: Hello from Nabis, This email is being sent in regards to the scheduled delivery coming your way on Wednesday, September 30, 2026. Attached are the invoice/manifest and COAs for Proof Operations, Inc. - 1058922 on Net 60. To confirm that you can receive this delivery, please click below: Confirm Delivery Our driver will give you a call prior to arrival with an ETA. As a friendly reminder, we ask

## 9. email `56435775-0dfc-4385-b853-548c3b0bf202`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: AP forward of Nabis shipping confirmation (invoice/manifest) 1042354, empty body | field recheck: bare forward; number matches subject; no amount visible
- your verdict: 

> EMAIL Subject: Fwd: #1042354 Shipping Confirmation + COAs: Natura <> EAZE Silver Lake [CS Group Operation, Inc.] for 09/10/2026 From: Accounts Payable <ap@eaze.com> Attachments: ['1042354_Natura_EAZE-Silver-Lake-CS-Group-Operation-Inc-_09-10-2026-1788892121710.pdf'] Body: 

## 10. email `68f8898c-912c-4dd4-bbe3-c988b6b7c838`
- **gold:** invoice   ·  **pipeline:** other (by llm)
- gold note: AP forward of 18 Kiva invoice PDFs, no substantive body | field recheck: bulk forward of 18 invoice PDFs; all filenames matched
- your verdict: 

> EMAIL Subject: Re: CA From: Accounts Payable <ap@eaze.com> Attachments: ['X-846051.pdf', 'X-846048.pdf', 'X-846047.pdf', 'X-846050.pdf', 'X-847564.pdf', 'X-847562.pdf', 'X-846052.pdf', 'X-846055.pdf', 'X-847560.pdf', 'X-847561.pdf', 'X-846054.pdf', 'X-846053.pdf', 'X-847563.pdf', 'X-846049.pdf', 'X-845504.pdf', 'X-846095.pdf', 'X-847559.pdf', 'X-846096.pdf'] Body: *Eaze Accounts Payable Team * Send all *invoices* to *AP@Eaze.com* for processing. You will NOT get a response from this email address. For all *payment inquiries*, email *APInquiries@Eaze.com* and we will respond within 24-48 hrs. On Thu, Aug 27, 2026 at 3:40 PM Accounts Payable <ap@eaze.com> wrote: > > *Eaze Accounts Payable Team

## 11. email `71a99387-e736-428a-83f9-987a94c88721`
- **gold:** invoice   ·  **pipeline:** invoice (by rule)
- gold note: -
- your verdict: 

> EMAIL Subject: Invoice for Eaze PO-154718 to Eaze Depot (CA) - Lincoln From: <ims@stachs.co> Attachments: [] Body: Dear Eaze Depot (CA) - Lincoln, Here is the invoice BILL/2026/1168* for Eaze PO-154718. Invoice #:* 248262 Amount: *$ 1,342.48 From:* Jeeter, Delivered by:* Med For America, Please remit payment per the vendor's payment terms. Please add the invoice to the vendor bill. Do not hesitate to contact us if you have any questions. Stachs Supply Chain supplychaingmgt@stachs.co [1] .... [1] Mailto:supplychaingmgt@stachs.co

## 12. email `ce8608dc-924a-49e0-a4fb-f544606efffa`
- **gold:** remittance   ·  **pipeline:** remittance (by rule)
- gold note: Republic Services payment confirmation
- your verdict: 

> EMAIL Subject: Thank You for Your Payment From: <noreply@republicservices.com> Attachments: [] Body: 09/14/2026 Dear Accounting Dept, Thank you for your payment of $270.70 Reference ID 564042604052 for account 305350108771 made on 09/14/2026. Please allow 48 hours for your payment to post to your account. If you have any questions please contact Customer Service online at RepublicServices.com. Thank you for being a valued customer and using Republic Services Online Bill Pay. Sincerely, Republic Services Customer Resource Center Please do not reply to this message, it was system generated and the mailbox is not monitored. Disclaimer: This message has been sent under the Republic Services Term

## 13. document `fil_4xype3ys`
- **gold:** invoice   ·  **pipeline:** invoice (by llm)
- gold note: Nabis invoice/manifest
- your verdict: 

> DOCUMENT Filename: 981951_GoldDrop-Coachella-Labs-_Eaze-Van-Nuys-Retail-HEALTHY-HERBAL-CARE-INC-_06-26-2026-1782512150437.pdf Text: ORDER # 981951 INVOICE # 981951-A PO / SO #PO-148194 Departure Time 06/26/2026 ETA 06/26/2026 :: 10:30-11:00 Actual Arrival Time Contact GoldDrop (Coachella Labs) Phone # (510) 372-1120 Email joseph@golddropco.com RECIPIENT: Healthy Herbal Care, Inc. | D.B.A. Eaze Van Nuys Retail [HEALTHY HERBAL CARE, INC] ORIGIN: NABIS LA - Garden of Weeden, INC. Address 7123 Sepulveda Blvd, Va- n Nuys, CA 91405 Recipient Contact Isaac Anderson Phone # (313) 701-6948 Email isaac.anderson@eaze.com State License C10-0000526-LIC Address 1816 E. Olympic Blvd, Los Angeles, CA 90021 

## 14. email `7e017506-6abc-4699-97a4-5108679a2bfa`
- **gold:** invoice   ·  **pipeline:** invoice (by rule)
- gold note: -
- your verdict: 

> EMAIL Subject: Invoice for Eaze PO-152497 to Eaze Depot (CA) - Budget King From: <ims@stachs.co> Attachments: ['PO-152497 - Timeless.pdf'] Body: Dear Eaze Depot (CA) - Budget King, Here is the invoice BILL/2026/1329* for Eaze PO-152497. Invoice #:* X-849115 Amount: *$ 123.96 From:* Timeless Select LLC, Delivered by:* Timeless Select LLC Please remit payment per the vendor's payment terms. Please add the invoice to the vendor bill. Do not hesitate to contact us if you have any questions. Stachs Supply Chain supplychaingmgt@stachs.co [1] .... [1] Mailto:supplychaingmgt@stachs.co

## 15. email `97083a43-d69d-414c-bd42-55d159bfc2a7`
- **gold:** invoice   ·  **pipeline:** invoice (by llm)
- gold note: Nabis shipping confirmation with invoice/manifest attached; fields null; 1054513 visible | field recheck: no amount visible in email
- your verdict: 

> EMAIL Subject: #1054513 Shipping Confirmation + COAs: Pacific Stone - Twisted Roots Inc. <> EAZE San Diego Delivery [ECSD MANAGEMENT LLC] for 09/23/2026 From: <deliveries-socal@nabis.com> Attachments: ['1054513_Pacific-Stone---Twisted-Roots-Inc-_EAZE-San-Diego-Delivery-ECSD-MANAGEMENT-LLC-_09-23-2026-1789738729888.pdf'] Body: Hello from Nabis, This email is being sent in regards to the scheduled delivery coming your way on Wednesday, September 23, 2026. Attached are the invoice/manifest and COAs for Pacific Stone - Twisted Roots Inc. - 1054513 on Net 60. To confirm that you can receive this delivery, please click below: Confirm Delivery Our driver will give you a call prior to arrival with a

## 16. document `fil_4xyrdjo4`
- **gold:** invoice   ·  **pipeline:** invoice (by llm)
- gold note: Nabis invoice
- your verdict: 

> DOCUMENT Filename: 1029944_Pacific-Stone---Twisted-Roots-Inc-_Eaze-Van-Nuys-Delivery-HEALTHY-HERBAL-CARE-INC-_08-26-2026-1787594910120.pdf Text: ORDER # 1029944 INVOICE # 1029944-A PO / SO PO-152205 Departure Time 08/26/2026 ETA 08/26/2026 :: 08:30-14:30 Actual Arrival Time Contact Pacific Stone - Twisted Roots Inc. Phone # (516) 924-3449 Email anthony@pacstone.com RECIPIENT: Healthy Herbal Care, Inc. | D.B.A. Eaze Van Nuys Delivery [HEALTHY HERBAL CARE, INC] ORIGIN: NABIS LA - Garden of Weeden, INC. Address 7123 Sepulveda Blvd, Va- n Nuys, CA 91405 Recipient Contact Isaac Anderson Phone # (707) 653-5447 Email isaac.anderson@eaze.com State License C10-0000526-LIC Address 1816 E. Olympic Blvd

## 17. document `fil_4xyorztg`
- **gold:** invoice   ·  **pipeline:** invoice (by llm)
- gold note: Nabis invoice
- your verdict: 

> DOCUMENT Filename: 1000198_Mr-Zips_EAZE-Sacramento-BUDGET-KING-LLC-_07-20-2026-1784583018057.pdf Text: ORDER # 1000198 INVOICE # 1000198-A PO / SO PO-149438 Departure Time 07/20/2026 ETA 07/20/2026 :: 12:00-15:00 Actual Arrival Time Contact Mr. Zips Phone # Email nickb@goheadwaters.com RECIPIENT: BUDGET KING, LLC | D.B.A. EAZE Sacramento [B- UDGET KING, LLC] ORIGIN: NABIS OAKLAND - Nabitwo, LLC Address 1750 Iris Ave, Suite 106, S- acramento, CA 95815 Recipient Contact Matt Sit Phone # (916) 583-8106 Email deliveries-budgetking@eaze.- com State License C9-0000041-LIC Address 5733 San Leandro St, Suite A & B, Oakland, CA 94621 Origin Contact Nabitwo, LLC Phone # 510-394-1858 Email help@nabis.c

## 18. document `fil_4xypxo7o`
- **gold:** invoice   ·  **pipeline:** invoice (by rule)
- gold note: Zoom invoice already paid (balance 0); total 1,589.39
- your verdict: 

> DOCUMENT Filename: INV363658295_A00223149_07272026.pdf Text: Invoice Zoom Communications, Inc. 55 Almaden Blvd, 6th Floor San Jose, CA 95113 Invoice Date: Invoice #: Payment Terms: Due Date: Account Number: Currency: Payment Method: Account Information: Account Legal Name: Sold To Address: Bill To Address: Jul 27, 2026 INV363658295 Net 30 Aug 26, 2026 532953 USD Eaze Eaze 160 Pine St. STE#350, San Francisco, California 94111 United States (+1) 317.364.6151 allen.shvarts@eaze.com 2800 3RD ST, SAN FRANCISCO, California 94107 United States 215-901-6026 ap@eaze.com Federal Employer ID Number: 61-1648780 For ACH and Wire Transfer payment: Account Name: Zoom Communications, Inc. Bank Name: Wells F

## 19. email `cbd0a5af-c886-48ac-bb6c-50745a9d4218`
- **gold:** invoice   ·  **pipeline:** invoice (by rule)
- gold note: QuickBooks 'needs your attention' without overdue language; PO-150745 $377.40; fields null
- your verdict: 

> EMAIL Subject: Invoice PO-150745 needs your attention From: Punch Distribution <quickbooks@notification.intuit.com> Attachments: ['Invoice_PO150745_from_Punch_Distribution.pdf'] Body: Your invoice is ready! BALANCE DUE$377.40 View and pay Hi EAZE - Growcery (DELIVERY), Invoice PO-150745 needs your attention. Please take a look at the attached invoice and contact us if you have any questions. Thanks, Punch Distribution View and pay Punch Distribution 8724 Remmet Ave Canoga Park, CA 91304 accounting@punchedibles.com +1 (323) 902-7320 www.punchedibles.com If you receive an email that seems fraudulent, please check with the business owner before paying, or you can forward the email to security@i

## 20. document `fil_4ykbs2j8`
- **gold:** invoice   ·  **pipeline:** invoice (by rule)
- gold note: Cintas invoice, total 825.31
- your verdict: 

> DOCUMENT Filename: Cintas Invoice # 4284106537 09_30_2026.PDF Text: REMIT PAYMENT TO: PAY YOUR BILL WITH MYCINTAS WWW.CINTAS.COM/MYACCOUNT MANAGE | SHOP | PAY CINTAS CORP P.O. BOX 630910 CINCINNATI, OH 45263-0910 CUSTOMER SVC/BILLING CINTAS FAX # 833-290-0514 386-274-2371 INVOICE SHIP TO: GREEN DRAGON LLC 160 COMFORT RD PALATKA, FL 32177-8636 BILL TO: GREEN DRAGON LLC 160 COMFORT RD PALATKA, FL 32177-8636 INVOICE # INVOICE DATE SERVICE TICKET # 4284106537 09/30/2026 4284106537 SOLD TO # PAYER # PAYMENT TERMS SORT # CINTAS ROUTE 25581290 25581290 NET 10 EOM 01490002888 13 / DAY 3 / STOP 007 EMP#/LOCK# MATERIAL DESCRIPTION FREQ EXCH QTY UNIT PRICE LINE TOTAL TAX X1045 60" MOP FRAME- 01 F 10 0.
