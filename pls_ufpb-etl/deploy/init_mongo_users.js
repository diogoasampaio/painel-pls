// Roda uma vez na VM B, via mongosh, para criar os dois usuarios do banco
// painel_pls -- um so leitura para a API, um leitura+escrita para o ETL --
// e os indices usados pelas agregacoes da API.
//
// Troque as senhas ANTES de rodar. Com security.authorization "enabled",
// conecte primeiro como admin:
//   mongosh -u admin -p --authenticationDatabase admin
//
// Uso: mongosh painel_pls deploy/init_mongo_users.js

db.createUser({
  user: "etl_user",
  pwd: "TROCAR_ANTES_DE_RODAR",
  roles: [{ role: "readWrite", db: "painel_pls" }],
});

// A API le tudo e so INSERE nas colecoes dos formularios (nunca altera nem
// apaga: o historico de envios e a trilha de auditoria).
db.createRole({
  role: "formulariosInsert",
  privileges: [
    { resource: { db: "painel_pls", collection: "pls_form_acompanhamento" }, actions: ["insert"] },
    { resource: { db: "painel_pls", collection: "pls_form_valores" }, actions: ["insert"] },
  ],
  roles: [],
});

db.createUser({
  user: "api_user",
  pwd: "TROCAR_ANTES_DE_RODAR",
  roles: [{ role: "read", db: "painel_pls" }, { role: "formulariosInsert", db: "painel_pls" }],
});
// Banco ja criado com a versao anterior deste script: rode so o createRole acima e
//   db.grantRolesToUser("api_user", [{ role: "formulariosInsert", db: "painel_pls" }]);

// Chave de substituicao de cada colecao (delete_many por ela) + filtros da API
db.pls_indicadores.createIndex({ periodo: 1, tema_codigo: 1, metrica: 1 });
db.pls_indicadores.createIndex({ ano: 1, tema_codigo: 1 });
db.pls_despesas.createIndex({ periodo: 1 });
db.pls_despesas.createIndex({ tema_codigo: 1, ano: 1 });
db.pls_empenhos.createIndex({ periodo: 1 });
db.pls_itens_empenho.createIndex({ periodo: 1 });
db.pls_itens_empenho.createIndex({ regras_texto: 1 });
db.pls_viagens.createIndex({ ano: 1 });
db.pls_trechos.createIndex({ ano: 1 });
db.pls_ipca.createIndex({ periodo: 1 }, { unique: true });
db.pls_comunidade.createIndex({ ano: 1, co_ies: 1 }, { unique: true });

db.pls_saude_carga.createIndex({ execucao: -1 });
db.pls_form_acompanhamento.createIndex({ acao_id: 1, ciclo: 1, registrado_em: -1 });
db.pls_form_valores.createIndex({ indicador_id: 1, ano: 1, registrado_em: -1 });
db.pls_form_acessos.createIndex({ hash: 1 }, { unique: true });
db.pls_form_acessos.createIndex({ setor: 1 }, { unique: true });

// colecoes do nucleo ampliado, das quantidades adquiridas e dos pedidos do AVN
db.pls_execucao.createIndex({ chave: 1, nivel: 1, ano: 1 });
db.pls_metas.createIndex({ indicador_id: 1, ano: 1 });
db.pls_itens_quantidade.createIndex({ ano: 1, familia: 1 });
db.pls_avn_itens.createIndex({ ano: 1 });
db.pls_avn_itens.createIndex({ pedido: 1 });

print("Usuarios e indices criados. Atualize MONGO_URI nos .env do backend (api_user) e do ETL (etl_user).");
