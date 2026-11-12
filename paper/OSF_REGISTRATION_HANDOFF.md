# Pré-registro externo do KAIRIS no OSF

Use o [rascunho científico](OSF_SECONDARY_DATA_PREREGISTRATION_DRAFT_v1.md)
e o anexo local `output/osf_external_validation_bundle_v1_p2_corrected.zip`.
O SHA-256 do ZIP revisado é
`0bf61ea0c06847fbd4aa5962f9864afa48e558f4fba6ae0502f3221dfc5869ee`.
O manifesto identifica o congelamento original e a fonte do analisador com a
correção de P2 (`eb3917b`).

1. O coordenador confirma os aceites e as declarações exigidas no registro
   privado. Use somente os papéis A, B e R nos materiais públicos.
2. No OSF, crie um rascunho **Secondary Data Preregistration**. A opção de
   começar do zero permite selecionar o ZIP explicitamente. Confira os campos
   preenchidos, metadados e anexos antes da submissão. [Guia oficial do OSF](https://help.osf.io/article/330-create-a-preregistration)
3. Defina a visibilidade. Se escolher embargo, registre também sua data final.
   O OSF bloqueia edições no registro submetido e nos anexos associados.
   [Privacidade e submissão no OSF](https://help.osf.io/article/330-create-a-preregistration)
4. Após a confirmação pelo OSF, registre o identificador, a data, a visibilidade
   e o hash do ZIP em `paper/EXTERNAL_VALIDATION_REGISTRATION_RECORD.json`.
   O verificador lê `osf_registration_id`, `osf_registered_at` e
   `coordinator_verified_registered_package`. Marque a verificação somente
   após confrontar o anexo registrado com o ZIP revisado.
5. A liberação explícita pelo coordenador usa `analysis_unlocked`. Rode
   `python scripts/check_external_validation_readiness.py` para conferir todos
   os gates antes de iniciar a validação externa.

O rascunho e o ZIP estão preparados localmente. Os aceites e as declarações
privadas, a visibilidade e a confirmação do registro seguem como ações pendentes.
