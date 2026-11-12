# Kotlinx Serialization keeps generated serializers
-keepattributes *Annotation*, InnerClasses
-keep,includedescriptorclasses class in.kisancoldlink.app.**$$serializer { *; }
-keepclassmembers class in.kisancoldlink.app.** { *** Companion; }
