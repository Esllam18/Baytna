import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Screen } from "../../src/ui/Screen";
import { EmptyState, ErrorState, LoadingState } from "../../src/ui/StateViews";
import { useNotifications, useNotificationSummary } from "../../src/hooks/useAccount";
import { customerApi } from "../../src/api";
import { queryKeys } from "../../src/query/keys";
import { colors, radius, spacing } from "../../src/theme/tokens";

export default function NotificationsScreen() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const q = useNotifications(unreadOnly);
  const summary = useNotificationSummary();
  const qc = useQueryClient();

  const refresh = () => Promise.all([
    qc.invalidateQueries({ queryKey: queryKeys.notifications }),
    qc.invalidateQueries({ queryKey: queryKeys.notificationSummary }),
  ]);

  const readOne = useMutation({
    mutationFn: (id: string) => customerApi.markNotificationRead(id),
    onSuccess: refresh,
  });
  const readAll = useMutation({
    mutationFn: () => customerApi.markAllNotificationsRead(),
    onSuccess: refresh,
  });

  if (q.isLoading) return <Screen><LoadingState label="بنجيب إشعاراتك..." /></Screen>;
  if (q.isError) return <Screen><ErrorState message="تعذر تحميل الإشعارات." /></Screen>;

  return (
    <Screen>
      <View style={s.header}>
        <Text onPress={() => router.back()} style={s.back}>→</Text>
        <View style={{ flex: 1 }}>
          <Text style={s.title}>الإشعارات</Text>
          <Text style={s.sub}>{summary.data?.unread_count ?? 0} غير مقروء</Text>
        </View>
      </View>

      <View style={s.toolbar}>
        <Pressable onPress={() => setUnreadOnly(!unreadOnly)} style={[s.filter, unreadOnly && s.filterActive]}>
          <Text style={[s.filterText, unreadOnly && s.filterTextActive]}>{unreadOnly ? "غير المقروء فقط" : "كل الإشعارات"}</Text>
        </Pressable>
        {(summary.data?.unread_count ?? 0) > 0 ? (
          <Text onPress={() => readAll.mutate()} style={s.readAll}>تحديد الكل كمقروء</Text>
        ) : null}
      </View>

      {q.data?.length ? q.data.map((item) => (
        <Pressable
          key={item.id}
          onPress={() => {
            if (!item.read_at) readOne.mutate(item.id);
            if (item.action_url?.startsWith("/")) router.push(item.action_url as never);
          }}
          style={[s.card, !item.read_at && s.unread]}
        >
          <View style={[s.dot, item.read_at && s.dotRead]} />
          <View style={s.body}>
            <Text style={s.itemTitle}>{item.title}</Text>
            <Text style={s.itemBody}>{item.body}</Text>
            <Text style={s.date}>{new Date(item.created_at).toLocaleString("ar-EG")}</Text>
          </View>
        </Pressable>
      )) : <EmptyState title="مفيش إشعارات" body="تحديثات الطلبات والدعم هتظهر هنا." />}
    </Screen>
  );
}

const s=StyleSheet.create({
  header:{flexDirection:"row-reverse",alignItems:"center",gap:12,paddingTop:14,paddingBottom:14},
  back:{fontSize:26},title:{fontSize:22,fontWeight:"900",color:colors.ink,textAlign:"right"},
  sub:{fontSize:11,color:colors.muted,textAlign:"right",marginTop:2},
  toolbar:{flexDirection:"row-reverse",justifyContent:"space-between",alignItems:"center",marginBottom:14},
  filter:{paddingVertical:8,paddingHorizontal:12,borderRadius:radius.pill,backgroundColor:colors.soft},
  filterActive:{backgroundColor:colors.orangeSoft},filterText:{fontSize:11,color:colors.muted},
  filterTextActive:{color:colors.orangeDark,fontWeight:"900"},readAll:{color:colors.orangeDark,fontSize:11,fontWeight:"800"},
  card:{flexDirection:"row-reverse",gap:10,borderBottomWidth:1,borderBottomColor:colors.border,paddingVertical:14},
  unread:{backgroundColor:"#FFF8EF",marginHorizontal:-8,paddingHorizontal:8,borderRadius:10},
  dot:{width:9,height:9,borderRadius:5,backgroundColor:colors.orange,marginTop:6},dotRead:{backgroundColor:"#D7CEC6"},
  body:{flex:1},itemTitle:{fontWeight:"900",color:colors.ink,textAlign:"right",writingDirection:"rtl"},
  itemBody:{fontSize:12,color:colors.muted,lineHeight:19,textAlign:"right",writingDirection:"rtl",marginTop:4},
  date:{fontSize:9,color:"#9B8F85",marginTop:5,textAlign:"right"}
});
