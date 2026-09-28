import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_agent', '0002_message_file_embedding'),
    ]

    operations = [
        # Ativa a extensão pgvector (idempotente)
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS vector;',
            reverse_sql=migrations.RunSQL.noop,
        ),

        migrations.CreateModel(
            name='FileIndex',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(max_length=255, verbose_name='nome do arquivo')),
                ('total_rows', models.IntegerField(default=0, verbose_name='total de linhas')),
                ('total_chunks', models.IntegerField(default=0, verbose_name='total de chunks')),
                ('done_chunks', models.IntegerField(default=0, verbose_name='chunks concluídos')),
                ('status', models.CharField(
                    choices=[
                        ('indexing', 'Indexando'),
                        ('processing', 'Processando'),
                        ('done', 'Concluído'),
                        ('error', 'Erro'),
                    ],
                    default='indexing',
                    max_length=20,
                    verbose_name='status',
                )),
                ('column_mapping', models.JSONField(blank=True, null=True, verbose_name='mapeamento de colunas')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('message', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='file_index',
                    to='ai_agent.message',
                    verbose_name='mensagem',
                )),
                ('conversation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='file_indexes',
                    to='ai_agent.conversation',
                    verbose_name='conversa',
                )),
            ],
            options={
                'verbose_name': 'Índice de Arquivo',
                'verbose_name_plural': 'Índices de Arquivo',
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='FileChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.IntegerField(verbose_name='índice do chunk')),
                ('row_start', models.IntegerField(verbose_name='linha inicial')),
                ('row_end', models.IntegerField(verbose_name='linha final')),
                ('content', models.TextField(verbose_name='conteúdo')),
                ('embedding', models.JSONField(blank=True, null=True, verbose_name='embedding')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendente'),
                        ('processing', 'Processando'),
                        ('done', 'Concluído'),
                        ('error', 'Erro'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='status',
                )),
                ('result_summary', models.JSONField(blank=True, null=True, verbose_name='resultado')),
                ('error_detail', models.TextField(blank=True, verbose_name='detalhe do erro')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('file_index', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chunks',
                    to='ai_agent.fileindex',
                )),
            ],
            options={
                'verbose_name': 'Chunk de Arquivo',
                'verbose_name_plural': 'Chunks de Arquivo',
                'ordering': ['file_index', 'chunk_index'],
                'unique_together': {('file_index', 'chunk_index')},
            },
        ),
    ]
