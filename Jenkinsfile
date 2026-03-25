pipeline {
    agent any

    environment {
        // Configuración de destino
        EC2_USER         = 'ubuntu'
        EC2_IP           = '18.219.33.101'
        REMOTE_DIR       = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        
        // Variables de Odoo
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        ODOO_PORT            = branchPort()
        POSTGRES_DB          = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        POSTGRES_USER        = 'odoo'
        POSTGRES_PASSWORD    = credentials('odoo-db-password')
    }

    stages {
        stage('Deploy to EC2') {
            steps {
                // Usamos la credencial de tu archivo .pem
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        # 1. Crear carpeta remota si no existe
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        
                        # 2. Sincronizar archivos (Dockerfiles, compose, addons) a la EC2
                        # Nota: scp es simple, rsync es mejor si está instalado
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        # 3. Ejecutar el despliegue remotamente
                        ssh ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            # Exportamos variables para que el docker-compose remoto las lea
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                            
                            docker compose up -d --build --remove-orphans
                            
                            echo "Esperando a que Odoo inicie..."
                            sleep 15
                            
                            # 4. Actualizar módulos
                            docker compose exec -T odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            docker compose restart odoo
EOF
                    '''
                }
            }
        }
    }

    post {
        failure {
            sshagent(['ec2-odoo-key']) {
                sh 'ssh ${EC2_USER}@${EC2_IP} "cd ${REMOTE_DIR} && docker compose logs odoo --tail=50"'
            }
        }
    }
}

def branchPort() {
    switch (env.BRANCH_NAME) {
        case 'main':    return '8071'
        case 'staging': return '8070'
        default:        return '8069'
    }
}