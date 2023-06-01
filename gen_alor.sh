sed -i -e 's:"Ценные бумаги / инструменты":instruments:g' alor.yaml
sed -i -e 's:"Работа с заявками":orders:g' alor.yaml
sed -i -e 's:-  "Другое":-  other:g' alor.yaml
sed -i -e 's:"Информация о клиенте":client:g' alor.yaml
sed -i -e 's:"Подписки и события (WebSocket)":subscriptions:g' alor.yaml
sed -i -e 's:"orders":orders:g' alor.yaml
rm -rf alor_client/*
/media/Data/Soft/jdk-18.0.2.1/bin/java -cp /home/inferno/.dev/Borgs/rustLibrary/target/rust-swagger-codegen-1.0.0.jar:/home/inferno/.dev/Borgs/rustLibrary/target/icu4j.jar:modules/swagger-codegen-cli/target/swagger-codegen-cli.jar io.swagger.codegen.v3.cli.SwaggerCodegen generate -l rust -i alor.yaml -o alor_client
sed -i -e 's:unnamed:alor-api:g' alor_client/Cargo.toml
