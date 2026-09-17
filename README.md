# MatCap for FreeCAD

Materialvisning rett i 3D-vinduet, uten renderer. Ingen lysoppsett, ingen
eksport, ingen ventetid: én tekstur og en GLSL-shader i Coin3D-scenegrafen.

En matcap er et bilde av en kule belyst i view-space. Shaderen slår opp i
teksturen med normalens xy-komponenter, og får lys, spekularitet og
miljørefleksjon i samme oppslag. Derfor ser det ut som metall i sanntid.

Oppå det ligger tre ting til: prosedyrisk overflateruhet med fysiske mål,
kavitetsskygge i fordypninger, og blyantskravering i fire trinn.

## Installasjon

**Med Addon Manager.** Tools → Addon Manager → tannhjulet → Custom
repositories, legg til repoets URL, og installer MatCap fra listen.

**Manuelt.** Kopier eller lenk `MatCap.FCMacro`, `MatCap.svg` og mappen
`matcaps/` inn i FreeCADs makromappe. Merk at FreeCAD 1.1 bruker en
versjonert mappe:

```bash
ln -sfn "$PWD/MatCap.FCMacro" ~/Library/Application\ Support/FreeCAD/v1-1/Macro/
ln -sfn "$PWD/matcaps" ~/Library/Application\ Support/FreeCAD/v1-1/Macro/
```

Riktig sti finner du alltid med `FreeCAD.getUserMacroDir(True)` i
Python-konsollen.

Krever FreeCAD 1.0 eller nyere. Ingen avhengigheter utover det FreeCAD
allerede har: pivy, PySide og Coin3D.

## Innhold

| Fil | Hva det er |
| --- | --- |
| `MatCap.FCMacro` | Makroen, med panel for valg av materiale |
| `matcaps/` | Femten teksturer i fire familier |
| `package.xml` | Metadata for Addon Manager |
| `make_matcaps.py` | Lager teksturene |
| `preview.py` | Viser en matcap på en form, uten FreeCAD |
| `import_blender_matcaps.py` | Henter Blenders matcaps og konverterer dem |
| `make_hatch_sheet.py` | Referanseark for skravering tegnet for hånd |
| `demo_wheel.py` | Bygger et riflet ratt som testobjekt |
| `verify_scale.py` | Måler at overflatene har størrelsen de heter |

Bare de tre øverste trengs for å bruke addonen. Resten er verktøyene som
laget den, og de følger med så settet kan bygges på nytt.

Panelet leser bare toppnivået i `matcaps/`. Legger du noe i en undermappe,
er det tilgjengelig uten å rote til listen.

## Se en matcap uten å starte FreeCAD

```bash
python3 preview.py metal_anodised --blast 0.12
python3 preview.py metal_anodised --shape sphere
```

Standardformen er en avrundet kasse med fas, ikke en kule. En kule gjengir
bare teksturen slik den allerede er, så den sier ingenting nytt; det er
flatene og fasen som avslører om materialet holder. Panelet i FreeCAD viser
kuler, og det er riktig der, for der skal du kjenne igjen teksturen.

Kornet oppgis i millimeter på emnet. Under omtrent 0,3 mm er det mindre
enn en piksel, og leses som en svak mykning i stedet for prikker. Slik er
det i virkeligheten også: blåsemønsteret du ser i produktfoto er makro.

## Materialene

| Familie | Teksturer |
| --- | --- |
| Metall | `metal_steel`, `metal_alu`, `metal_dark`, `bl_metal_full` |
| Anodisert | `metal_anodised`, `metal_anodised_light` |
| Leire | `clay_light`, `clay_warm`, `bl_clay_studio` |
| Lys plast | `plast_white`, `plast_grey`, `plast_cream`, `print_pla_grey` |
| Trinnvis | `toon_paper`, `toon_sky`, `toon_clay`, `toon_moss` |

### Anodisert aluminium

Mørkt, matt og kulepolert, slik frest aluminium ser ut i et hvitt
produktstudio. Tre valg gjør jobben, og to av dem er mot intuisjonen:

**Lav ruhet, men lav spekularitet.** Det høres selvmotsigende ut, men
blåst aluminium speiler ikke skarpt, samtidig som det fortsatt gjengir
taket som en bred lys flate og gulvet som en mørkere. Skrur man opp
ruheten, midles miljøet til én tone, og toppflaten og forsiden mister
forskjellen som gjør at formen leses.

**Metallverdi 0,72, ikke 1,0.** Full metallverdi fjerner det diffuse
leddet, og da er miljøet alene om å skape form. Med litt dielektrisk igjen
får flatene vanlig formskygge også.

**Lyst gulv i miljøet, men ikke like lyst som taket.** Et hvitt studio gjør
at undersiden blir mørk grå i stedet for svart. Gjør man gulvet nesten like
lyst som taket, forsvinner formen igjen. Begge grøftene var innom underveis.

Bruk dem med Sandblåst 0,05 mm, som automatikken velger selv.

### Trinnvise materialer

Fire flate fargefelt med myke skiller, i stedet for en gradient. En matcap
er en oppslagstabell, og ingenting krever at den er glatt. Legger vi inn
trinn, får vi rene terminatorlinjer uten å regne dem ut, og de holder seg
like rene uansett hvor tett geometrien er tessellert.

Hvert trinn har sin egen farge, ikke bare sin egen lyshet. Skyggene går
kjøligere og mer mettede, lysene varmere og blassere. Det er det som
skiller håndmalt fra en modell med kontrasten skrudd opp.

To ting måtte til før trinnene ble synlige:

**Ett nøkkellys, ikke tre.** Med flere lys krysser terminatorene hverandre,
trinnene blir uryddige flekker, og bunnlyset spiser opp det mørkeste
trinnet.

**Tersklene legges etter areal, ikke etter lysverdi.** Vi ser bare den
fremre halvkula, og nøkkellyset peker delvis mot oss, så lysverdiene
klumper seg i det lyse. Fordelt jevnt over tallområdet havnet tre av fire
trinn oppå hverandre, og materialet så ensfarget ut. Nå sier `TOON_CUTS`
hvor stor andel av flaten hvert trinn skal dekke, og generatoren finner
lysverdiene som gir den fordelingen.

De to `bl_`-teksturene er de eneste fra Blender som holder. Resten av settet
der er laget for sculpting, hvor man vil se formen uten at materialet
stjeler oppmerksomhet, så de er med vilje flate og mørke. `bl_metal_bronze`
er praktisk talt sort, og hard surface har knapt form i det hele tatt. De
ligger i `extra/`.

`make_matcaps.py` lager de ni andre matematisk, uten avhengigheter. Vil du
justere en farge eller lage en ny, står alle parametrene i `PRESETS`.

**Lysstyrken måles, den gjettes ikke.** To forsøk gikk galt før det satt.
Det første delte lyssummen på for lite, slik at hele oversiden av kula
klippet mot 1,0 og formen forsvant. Det neste delte på for mye, og hvit
plast kom ut grå. Nå går et raskt forpass over kula og finner hva de to
lysleddene faktisk når, og de tallene brukes som normalisering. Da stemmer
det uansett hvordan lysene flyttes.

## Bruk

Åpne panelet med **Macro → Macros…**, velg `MatCap` i listen og trykk
**Execute**. Panelet kommer som et eget vindu og kan stå åpent mens du
jobber.

Alt slår inn med én gang. Ett klikk på et materiale bytter det,
glidebryterne oppdaterer mens du drar, og markerer du noe nytt i
modelltreet følger materialet med. Uten markering behandles alle synlige
objekter i dokumentet.

Derfor er det ingen Bruk-knapp. Den eneste knappen er Fjern, som er den
eneste veien tilbake til FreeCADs egen visning.

Utvalget fanges opp av en observatør som bare lytter på `addSelection`.
Tømmer man utvalget skjer ingenting; ellers ville et klikk i tomrommet
plutselig lagt materialet på alt som er synlig.

Glidebryterne er dempet med 90 ms. De sender én verdi per piksel musa
flyttes, og uten forsinkelsen ville scenegrafen blitt bygget på nytt for
hver eneste av dem.

## Egne matcaps

Alle .png- og .jpg-filer i `matcaps/` dukker opp i panelet. Vil du lage
egne, endre `PRESETS` i `make_matcaps.py` og kjør den på nytt.

### Fra Blender

To `bl_`-teksturer kommer fra Blenders egen sculpt-modus. Vil du hente
dem på nytt, for eksempel etter en Blender-oppdatering:

```bash
python3 import_blender_matcaps.py
```

Blender lagrer dem som lineær EXR, som Coin ikke leser. Skriptet kjører
Blender i bakgrunnsmodus og lar den gjøre konverteringen til sRGB-PNG.
Fargetransformasjonen settes til Standard, ikke AgX eller Filmic; matcapene
er allerede ferdig gradet, og en filmisk kurve ville vasket ut kontrasten.

Debug-teksturene, `check_*`, hoppes over. De viser normaler og refleksjoner
for feilsøking, ikke materialer. Blenders matcaps er CC0.

### Andre kilder

| Kilde | Hva du får |
| --- | --- |
| `github.com/nidorx/matcaps` | Det store biblioteket, over 800 stykker, med forhåndsvisning og flere oppløsninger. |
| `github.com/hughsk/matcap` | Mindre samling, men jevn kvalitet og ryddige filnavn. |
| ArtStation og Gumroad | Søk «matcap», mange kunstnere deler sett gratis. |

Krav til bildet: kula skal fylle hele ruta, og bildet skal være kvadratisk.
Filtypene .png og .jpg fungerer begge.

## Hvordan det virker

Shaderen legges inn i objektets `RootNode` på indeks 1, altså etter
transformasjonen og foran resten av grafen.

Ikke legg den i `SwitchNode`. Det er en `SoSwitch` der `whichChild` peker
på gjeldende visningsmodus, og et nytt barn forskyver indeksen slik at
objektet forsvinner. Det var den første feilen i utviklingen.

Coin bruker gammel GLSL, så vertex-shaderen bruker `ftransform()` og
`gl_NormalMatrix * gl_Normal`. Det er akkurat det vi trenger her.

### Kantartefakter

Ved silhuetten er normalens xy nesten én lang, og oppslaget havner ytterst
i teksturen. Det ga striper langs konturen. Tre ting måtte på plass:

1. `wrapS` og `wrapT` settes til CLAMP. Coin bruker REPEAT som standard, så
   oppslaget wrappet rundt til motsatt side av bildet.
2. UV skaleres med 0.49 i stedet for 0.5, altså en liten margin inn.
3. Generatoren fyller flaten utenfor kula med kantfargen i stedet for
   svart, slik at bilineær filtrering ikke blander inn en mørk ring.

Bruker du nedlastede matcaps med svart bakgrunn, holder punkt 1 og 2.

### Overflate

En matcap gir materialet, men den kan ikke gi ruhet: alle punkter med samme
normal får samme farge, så en jevn flate blir jevn. Derfor forstyrres
normalen først, per piksel, og matcapen slås opp etterpå. Det er nøyaktig
det et normal map gjør, bare regnet ut i stedet for lest fra en tekstur.

Teksturen er sandblåst med 0,05 mm korn. Den er en avkryssing, ikke en
meny: ett godt valg slår fire middelmådige, og dette ene kler både metall
og plast. Automatikken slår den på for metall, plast og printplast, og lar
leire og de trinnvise materialene stå glatte.

**Målet er fysisk, ikke relativt til emnet.** Verktøyet vokser ikke med
delen: blåsemedia gir samme korn enten emnet er 1 cm eller 10 cm. Derfor er
skalaen perioder per millimeter.

Shaderen kan fortsatt dreide ringer og printlag, modus 1 og 3, men de er
ikke lenger i grensesnittet. Vil du ha dem tilbake, står de i `TEXTURE`
øverst i makroen.

### Måling av skalaen

Påstanden om millimeter er verdiløs uten en måling, så `verify_scale.py`
gjør den. En kube på nøyaktig 10 mm sett rett forfra: kubens høyde i piksler
gir målestokken, og antall lysheteopper nedover en kolonne gir antall
perioder.

Tabellen er fra da alle seks var i menyen. Bare den øverste er
eksponert nå, men shaderen kan fortsatt resten.

```
overflate                nominelt       målt    px/mm
Dreid 0,1 mm              0.100 mm    0.114 mm     64.2
Dreid 0,25 mm             0.250 mm    0.196 mm     56.0
Sandblåst 0,05 mm         0.050 mm    0.079 mm     52.8
Sandblåst 0,12 mm         0.120 mm    0.119 mm     52.2
Printlag 0,2 mm           0.200 mm    0.204 mm     52.0
Printlag 0,12 mm          0.120 mm    0.120 mm     52.0
```

Printlagene treffer eksakt, siden de er en ren sinus uten andre frekvenser.
De støybaserte ligger litt unna fordi de har en finere andreoktav oppå
grunnfrekvensen, og telleren fanger begge. Navnet viser grunnfrekvensen.

Målingen bommer også når periodene nærmer seg et par piksler. Da smelter
toppene sammen på skjermen, og da er tallet like upålitelig som bildet.

Sandblåst het opprinnelig 0,2 mm. Skalaen var riktig, men navnet var det
ikke: blåsemedia gir korn på hundredeler, ikke tideler, og flaten leste som
støpegods. Den grove heter nå 0,12 mm.

Auto-boksen velger etter materialfamilien: metall blir dreid, hard surface
sandblåst, leire står glatt, printplast får printlag. Velger du selv, slår
automatikken seg av.

Tre ting måtte være riktig for at dette skulle virke:

**Regn i objektrom, ikke view-space.** Mønsteret skal sitte fast på emnet
når kameraet roterer. Derfor sender vertex-shaderen `gl_Vertex` og
`gl_Normal` videre urørt, og fragment-shaderen transformerer til view-space
først etter at normalen er forstyrret. `gl_NormalMatrix` er en innebygd
uniform og er tilgjengelig også i fragment-shaderen, så det går fint.

**Bare komponenten langs flaten teller.** Stigningen i høydefeltet peker
hvor som helst. Trekker man ikke fra normalretningen, blir mønsteret en
oppblåsing i stedet for ruhet, og flater vendt mot lyset flimrer.

**Skalaen må normaliseres bort.** Uten det ville et finere mønster
automatisk gitt kraftigere utslag, og dybdeverdien betydd noe nytt for hver
overflate. Nå er skalaen perioder per millimeter, så tallene er fysiske:
5,0 er 0,2 mm lagtykkelse.

Printlagene legger seg av seg selv bare på loddrette flater og forsvinner
på topplanet. Det er ikke en regel i koden, det følger av at stigningen
langs Z projiseres bort når normalen peker rett opp. Slik oppfører en ekte
FDM-print seg også.

### Printplast

Blenders sett har ingen matcap for printet plast. Leire er for kritt, resin
for blank. `gen_print_matcap.py` lager tre: grå, sort og oransje.

Det som gjør dem til plast og ikke gips, er kantgløden og et wrapped
diffuse-ledd, altså at lyset får fortsette litt forbi terminatoren. Plast
sprer lys under overflaten, og uten det ser den ut som malt gips.

Første forsøk ble helt flatt. Summen av de tre lysene nådde over 1,0 og ble
klippet, så hele oversiden av kula var ensfarget. Deles det på 1,75 i
stedet, holder formen seg.

### Fordypninger

Krumningen finnes ved å sammenligne hvor mye normalen dreier med hvor
langt vi flyttet oss, mellom nabopiksler. Negativ krumning er konkav,
altså et hjørne eller en not, og det er der lys faktisk blir fanget.

Dette er kavitetsskygge, ikke ekte ambient occlusion. Forskjellen er verdt
å kjenne: den ser bare et par piksler ut, så en avrunding blir mørk, men en
eike kaster ingen skygge ned i lommen under. Ekte AO krever at hele scenen
rendres til en dybdetekstur og settes sammen igjen i en fullskjermspass.
`SoSceneTexture2` finnes med DEPTH i Coin, men den passen ligger over
FreeCADs eget kamera, og der kolliderer den med seleksjon, overlegg og
navigasjonskuben.

### Blyantskravering

Strekene tegnes i skjermrom, mot `gl_FragCoord`, ikke i teksturen. En
matcap kan bære skravering selv, men bare der normalen varierer: en plan
flate har én normal, altså ett oppslag, altså én flat farge og ingen
streker. På en CAD-modell full av plane flater blir det feil.

Lysheten deles i fire soner, samme prinsipp som de trinnvise matcapene:

| Sone | Teknikk |
| --- | --- |
| Mørkest | Tette streker, krysset i to retninger |
| Nest mørkest | Samme strek, nesten dobbelt så glissen |
| Nest lysest | Prikker, jittret rutenett med tomme celler |
| Lysest | Blankt papir |

Vinklene er med vilje ikke 90 grader fra hverandre. Kryssende streker i
rett vinkel leser som rutenett, ikke som skygge.

### Hvorfor skraveringen ikke måles i millimeter

Overflatene måles i millimeter fordi verktøyet står mot emnet: en dyse
legger 0,2 mm lag uansett hvor stor delen er. Blyanten står ikke mot
emnet, den står mot papiret. Strekbredden er en egenskap ved blyanten og
arket, ikke ved delen. Derfor er skraveringen fast i skjermpiksler, og
strekene blir like brede uansett hvor stor modellen er eller hvor langt du
zoomer.

Det er samme regel, anvendt på det verktøyet faktisk berører. Prisen er at
strekene ikke sitter fast på flaten når du roterer; de står stille mens
modellen beveger seg under dem, slik det ser ut når man tegner på glass.
Skal de sitte fast, må mønsteret regnes i objektrom, og da blir strekene
grovere jo nærmere du zoomer.

Strekene er tynne med vilje. Blyant bygger mørke med mange streker, ikke
med brede; for tykke streker gir gravyr. Hver strek har litt tilfeldig
tykkelse og varierer i styrke langs sin egen lengde, ellers ser det trykt
ut. Grafitt er heller ikke svart, men en kjølig mørk grå, så ren svart ser
ut som tusj.

Okklusjonen legges på før skraveringen, slik at mørkere hjørner også får
tettere streker.

### Kantlinjer

Shaderen legges i separatorene som inneholder flategeometrien, ikke i
rotnoden. Hver separator avgrenser tilstanden sin, så kanter og punkter
ligger utenfor og beholder sine egne farger. Avkryssingsboksen «Mørke
kantlinjer» setter dem til dempet grå, som er det Fusion gjør. Svart blir
for hardt og ser tegneserieaktig ut.

Alle visningsmodusene får shaderen, ikke bare den aktive, slik at
materialet står når du bytter mellom Flat Lines og Shaded.

**Tykkelsen ganges med skjermens pikselforhold.** `LineWidth` i Coin teller
fysiske piksler. På en skjerm med forhold 2, altså de fleste moderne, ga
verdien 1 en strek på en halv logisk piksel. Den forsvant delvis, og
kantene så stiplete ut der de krysset trekantkanter, tydeligst i riflingen
der kantene er korte og tette. Nå betyr 1,00 i panelet alltid én synlig
piksel, uansett skjerm.

## Testobjekt

Et flatt emne viser ingenting. `demo_wheel.py` bygger et riflet ratt,
Ø30 x 8,6 mm, med ti kuler rundt kanten, rifling på annenhver, fem lommer
og et senket nav. Ekte CAD-geometri med analytiske flater, ikke mesh.

Bygg det utenfor FreeCAD og åpne fila etterpå:

```bash
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd -c "import io; exec(io.open('demo_wheel.py', encoding='utf-8').read()); main('demo_wheel.FCStd')"
```

To ting var ikke åpenbare da modellen ble bygget:

**Avrund før du rifler.** Riflingen lager hundrevis av korte kanter som
møtes i spisse vinkler, og OCC gir opp hele filleten hvis den må forholde
seg til dem. Byttet man rekkefølge, gikk 36 kanter gjennom.

**Fillet én kant av gangen.** En samlet fillet feiler helt så snart én kant
er umulig. Tas de enkeltvis, mister man bare de problematiske. Skriptet
forkaster også kanter der avrundingen vokser utenfor omskrevet boks; en
fillet på en konkav kant legger på materiale, og der hakkene tangerer
ytterkanten ga det en vulst utenfor både diameteren og topplanet.

## Kjente begrensninger

* **Seleksjon vises ikke.** Den grønne markeringsfargen går gjennom Coins
  egen materialvei, og shaderen overstyrer den. Objektet er fortsatt
  markert, det ser bare ikke slik ut.
* **Ingen skygge.** Coin har noder for skyggekart, `SoShadowGroup` og
  `SoShadowStyle`, men de er ikke eksponert i pivy-bygget som følger med
  FreeCAD. En matcap gir deg lyset, ikke kastskyggen.
* **Sømlinjer vises.** Flat Lines tegner hver kant i topologien, også
  sømmen der en sylinderflate lukker seg. Fusion skjuler tangentkanter,
  FreeCAD har ikke den innstillingen.
* Endringene ligger bare i scenegrafen. De lagres ikke i FCStd-fila, og
  forsvinner når dokumentet lukkes.

## Advarsel: ikke bygg i bakgrunnstråd

Kjører du dokumentoppretting eller noe annet som åpner et vindu fra en
annen tråd enn hovedtråden, krasjer FreeCAD på macOS. Det ser ut som en
geometrifeil, men er det ikke: stacken ender i `NSWindow initWithContentRect`
med SIGABRT, fordi AppKit ikke tillater vindusoperasjoner utenfor
hovedtråden.

Tung geometri hører uansett hjemme i `freecadcmd`, ikke i GUI-tråden.
Bygg til en FCStd-fil og åpne den, slik `demo_wheel.py` legger opp til.

## Videre

* Skille kantene ut, så de beholder sin egen farge.
* Håndtere seleksjon, enten ved å fjerne shaderen for markerte objekter
  eller ved å blande inn markeringsfargen i fragment-shaderen.
* Pakke det som en ordentlig arbeidsbenk med verktøylinjeknapp.
* Lagre valgt matcap per objekt i dokumentet.
