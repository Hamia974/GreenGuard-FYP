// English is the reference message set: types/i18n.d.ts derives the typed
// `Messages` shape from this object, and messages/ur/index.ts must match it.
// A new screen = a new <namespace>.json here (and in ur/), listed below.
import admin from "./admin.json";
import auth from "./auth.json";
import common from "./common.json";
import crops from "./crops.json";
import dashboard from "./dashboard.json";
import disease from "./disease.json";
import diseases from "./diseases.json";
import errors from "./errors.json";
import farms from "./farms.json";
import history from "./history.json";
import home from "./home.json";
import language from "./language.json";
import legal from "./legal.json";
import metadata from "./metadata.json";
import navigation from "./navigation.json";
import notifications from "./notifications.json";
import profile from "./profile.json";
import quickScan from "./quickScan.json";
import report from "./report.json";
import soil from "./soil.json";
import units from "./units.json";
import upload from "./upload.json";
import validation from "./validation.json";
import weather from "./weather.json";

const messages = {
  admin,
  auth,
  common,
  crops,
  dashboard,
  disease,
  diseases,
  errors,
  farms,
  history,
  home,
  language,
  legal,
  metadata,
  navigation,
  notifications,
  profile,
  quickScan,
  report,
  soil,
  units,
  upload,
  validation,
  weather,
};

export default messages;
