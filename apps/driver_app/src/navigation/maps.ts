import * as Linking from "expo-linking";
import { DeliveryAddress } from "../api/types";

function mapsUrl(query:string) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

export async function navigateToPickup(name:string,area:string) {
  await Linking.openURL(mapsUrl(`${name}, ${area}`));
}

export async function navigateToDropoff(address:DeliveryAddress) {
  if (address.latitude && address.longitude) {
    await Linking.openURL(mapsUrl(`${address.latitude},${address.longitude}`));
    return;
  }
  const query=[
    address.area,address.street,address.building,address.floor,address.apartment,
  ].filter(Boolean).join(", ");
  await Linking.openURL(mapsUrl(query));
}
