import React from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { DailyMenuItem } from "../api/types";
import { colors, radius, shadow } from "../theme/tokens";
import { egp } from "../utils/format";
import { mediaUri } from "../utils/media";
export function DishCard({ item, chefName, onPress }: { item: DailyMenuItem; chefName?: string; onPress(): void }) {
  const uri=mediaUri(item.image_url); const sold=item.quantity_available<=0 || item.status==="sold_out";
  return <Pressable onPress={onPress} style={({pressed})=>[s.card,pressed&&s.pressed]}>{uri?<Image source={{uri}} style={s.image}/>:<View style={s.fallback}><Text style={s.emoji}>🍲</Text></View>}<View style={s.body}><Text numberOfLines={1} style={s.name}>{item.name}</Text>{chefName?<Text numberOfLines={1} style={s.meta}>من {chefName}</Text>:null}<Text style={sold?s.sold:s.available}>{sold?"نفدت الكمية اليوم":item.availability_label}</Text><Text style={s.price}>{egp(item.price_minor)}</Text></View></Pressable>;
}
const s=StyleSheet.create({card:{width:"48%",borderWidth:1,borderColor:colors.border,borderRadius:18,overflow:"hidden",backgroundColor:colors.surface,...shadow},image:{width:"100%",height:112,backgroundColor:colors.soft},fallback:{height:112,backgroundColor:"#FFE0BD",alignItems:"center",justifyContent:"center"},emoji:{fontSize:48},body:{padding:11},name:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},meta:{fontSize:11,color:colors.muted,marginTop:3,textAlign:"right",writingDirection:"rtl"},price:{color:colors.orangeDark,fontWeight:"900",fontSize:15,marginTop:5,textAlign:"right"},available:{fontSize:10,color:colors.greenDark,marginTop:4,textAlign:"right"},sold:{fontSize:10,color:colors.danger,marginTop:4,textAlign:"right"},pressed:{opacity:.8}});
